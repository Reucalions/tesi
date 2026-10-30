"""Bridge con HTTP Fablo simulato: nessuna esecuzione BWAF, Tiny-ME o Fabric."""

import json

import anyio
import httpx
import pytest
from mcp.shared.memory import create_connected_server_and_client_session
from support.fablo_fixture import SimulatedFablo
from test_camel_integration import ScriptedToolModel

from services.strategic_gateway.fablo import FabloClient, FabloError, FabloSettings
from services.strategic_gateway.fabric import FabricGateway, validate_annotated, validate_ranking
from services.strategic_gateway.fabric_server import create_server
from thesis_agents.backends import BackendSettings, connect_backends
from thesis_agents.fixtures import run_fixtures
from thesis_agents.mcp.client import MCPClient, decode_result, digest, schema_shape
from thesis_agents.mcp.fabric_client import native_call
from thesis_agents.mcp.fabric_contracts import (
    AnalyzeOntologyRequest,
    FabricResponse,
    GraphKey,
    NativeGraph,
    RecordProvenanceRequest,
    StoreGraphRequest,
    fabric_contracts,
)
from thesis_agents.mcp.settings import MCPSettings
from thesis_agents.orchestration.artifacts import ArtifactSession
from thesis_agents.orchestration.workforce import run_camel
from thesis_agents.schemas import CandidateStrategies, ProvenanceRecord
from thesis_agents.tools.fabric_provenance import FabricProvenanceTool, fabric_provenance_contracts
from thesis_agents.tools.ranking_mock import build_graph


@pytest.fixture
def record(session):
    run_fixtures(session)
    return session.require("provenance", ProvenanceRecord)


@pytest.fixture
def graph():
    return NativeGraph.model_validate(
        {
            "nodes": [
                {"id": "CVE_assertion", "type": "vulnerability"},
                {"id": "Upgrade", "type": "strategy"},
            ],
            "edges": [{"from": "CVE_assertion", "to": "Upgrade"}],
        }
    )


@pytest.fixture
def backend(monkeypatch):
    monkeypatch.setenv("THESIS_FABLO_SECRET", "test-only-secret")
    fake = SimulatedFablo()
    client = FabloClient(
        FabloSettings(url="http://fablo.test", secret_env="THESIS_FABLO_SECRET"),
        transport=httpx.MockTransport(fake),
    )
    yield FabricGateway(client), fake
    client.close()


def store(gateway, graph):
    graph_id = "graph:" + digest(graph.model_dump(mode="json", by_alias=True))
    gateway.store_graph(StoreGraphRequest(graph_id=graph_id, graph=graph))
    return GraphKey(graph_id=graph_id)


def test_graph_cycle_uses_native_routes_preserves_scores_and_explanations(backend, graph):
    gateway, fake = backend
    request = store(gateway, graph)
    ranked = gateway.rank_graph(request)
    assert ranked.verification == "peer-readback"
    assert ranked.result["ranking"][0]["score"] == 1.25
    assert "explanation" in ranked.result["ranking"][0]
    assert gateway.get_graph(request).result["graph"] == graph.model_dump(by_alias=True)
    assert gateway.get_rank_result(request).result["ranking"] == ranked.result["ranking"]
    assert gateway.get_annotated_graph(request).result["graph"]["edges"]
    writes_before = sum(body.get("method", "").endswith(":StoreGraph") for _, body in fake.calls)
    store(gateway, graph)
    assert (
        sum(body.get("method", "").endswith(":StoreGraph") for _, body in fake.calls)
        == writes_before
    )
    assert {path for path, _ in fake.calls} == {
        "/user/enroll",
        "/query/my-channel/argumentation",
        "/invoke/my-channel/argumentation",
    }


@pytest.mark.parametrize("fault", ["http", "accepted", "chaincode-error", "tampered-store"])
def test_graph_failure_is_never_reported_as_persisted(backend, graph, fault):
    gateway, fake = backend
    fake.fault = fault
    with pytest.raises(FabloError):
        store(gateway, graph)


def test_wrong_ranking_rejected_without_synthetic_fallback(backend, graph):
    gateway, fake = backend
    request = store(gateway, graph)
    fake.fault = "wrong-ranking"
    with pytest.raises(FabloError, match="strategies"):
        gateway.rank_graph(request)


def test_graph_requires_content_key_and_rejects_legacy_projection(backend, graph):
    gateway, fake = backend
    with pytest.raises(ValueError, match="SHA-256"):
        gateway.store_graph(StoreGraphRequest(graph_id="arbitrary", graph=graph))
    assert fake.calls == []
    with pytest.raises(ValueError):
        NativeGraph.model_validate(
            build_graph(CandidateStrategies(strategies=[]), "legacy").model_dump()
        )


@pytest.mark.parametrize("fault", [None, "tampered-reasoning", "missing-reasoning"])
def test_tinyme_requests_all_services_and_checks_readback(backend, fault):
    gateway, fake = backend
    fake.fault = fault
    request = AnalyzeOntologyRequest(
        ontology_key="analysis:test",
        ontology="Ontology(test-transport-only)",
        resource="Resource",
        request="Request",
    )
    request.ontology_key = request.content_key()
    if fault:
        with pytest.raises(FabloError):
            gateway.analyze_ontology(request)
    else:
        result = gateway.analyze_ontology(request)
        assert result.result["isCoherent"] is True
        assert "valid" not in result.result  # coerenza non equivale ad applicabilità.
        assert result.verification == "peer-readback"


@pytest.mark.parametrize("fault", [None, "tampered-provenance"])
def test_provenance_submits_full_record_and_jsonld_and_checks_digest(backend, record, fault):
    gateway, fake = backend
    fake.fault = fault
    request = RecordProvenanceRequest(record=record)
    if fault:
        with pytest.raises(FabloError, match="digest"):
            gateway.record_provenance(request)
    else:
        response = gateway.record_provenance(request)
        assert response.result["document"]["record"] == record.model_dump(mode="json")
        assert response.result["document"]["jsonld"]["@type"] == "prov:Bundle"
        assert response.result["tx_id"] == "synthetic-tx"
        assert response.chaincode == "thesis-provenance"


def test_mcp_discovery_and_complete_native_cycle(backend, graph, record):
    gateway, _ = backend

    async def exercise():
        async with create_connected_server_and_client_session(create_server(gateway)) as client:
            tools = {tool.name: tool for tool in (await client.list_tools()).tools}
            for name, (request_schema, response_schema) in fabric_contracts().items():
                actual = dict(tools[name].inputSchema)
                actual.setdefault("additionalProperties", False)
                assert schema_shape(actual) == schema_shape(request_schema), name
                assert schema_shape(tools[name].outputSchema) == schema_shape(response_schema)
            graph_id = "graph:" + digest(graph.model_dump(mode="json", by_alias=True))
            analysis = AnalyzeOntologyRequest(
                ontology_key="temporary",
                ontology="Ontology(test-transport-only)",
                resource="Resource",
                request="Request",
            )
            analysis.ontology_key = analysis.content_key()
            operations = [
                ("store_graph", {"graph_id": graph_id, "graph": graph.model_dump(by_alias=True)}),
                *[
                    (name, {"graph_id": graph_id})
                    for name in (
                        "get_graph",
                        "rank_graph",
                        "get_rank_result",
                        "get_annotated_graph",
                    )
                ],
                ("analyze_ontology", analysis.model_dump(mode="json")),
                ("get_reasoner_result", {"ontology_key": analysis.ontology_key}),
                ("record_provenance", {"record": record.model_dump(mode="json")}),
                ("read_provenance", {"run_id": record.run_id}),
            ]
            for name, arguments in operations:
                response = FabricResponse.model_validate(
                    decode_result(await client.call_tool(name, arguments))
                )
                assert response.operation == name
                assert response.request_sha256 == digest(arguments)

    anyio.run(exercise)


@pytest.mark.parametrize("score", [float("nan"), float("inf"), True, "0.5"])
def test_invalid_native_scores_are_rejected(graph, score):
    with pytest.raises(FabloError):
        validate_ranking([{"name": "Upgrade", "score": score}], graph)


def test_invalid_annotated_references_are_rejected():
    with pytest.raises(FabloError):
        validate_annotated(
            {
                "nodes": [{"data": {"id": 1}}],
                "edges": [{"data": {"source": 1, "target": 2, "label": 0.5}}],
            }
        )


def test_credentials_and_error_bodies_are_not_exposed(backend, monkeypatch):
    gateway, fake = backend
    monkeypatch.delenv("THESIS_FABLO_SECRET")
    with pytest.raises(FabloError, match="credential"):
        gateway.client.enroll()
    assert not fake.calls
    assert "test-only-secret" not in repr(gateway.client.settings)


@pytest.mark.parametrize("url", ["http://user:password@host", "http://host?token=secret"])
def test_fablo_rejects_credentials_in_url(url):
    with pytest.raises(ValueError):
        FabloSettings(url=url, secret_env="TEST_SECRET")


@pytest.mark.mcp_http
def test_native_http_client_and_workforce_provenance_adapter(http_server, graph, record, tmp_path):
    url = http_server(kind="fabric")
    with MCPClient(
        MCPSettings(url=url, expected_kind="real"), contracts=fabric_contracts()
    ) as client:
        graph_id = "graph:" + digest(graph.model_dump(mode="json", by_alias=True))
        native_call(client, "store_graph", graph_id=graph_id, graph=graph.model_dump(by_alias=True))
        result = native_call(client, "rank_graph", graph_id=graph_id)
        assert result.result["ranking"][0]["score"] == 1.25
        adapter = FabricProvenanceTool(
            client, tmp_path, channel="my-channel", chaincode="thesis-provenance"
        )
        receipt = adapter.record_provenance(record)
        assert adapter.verify_export(record) == receipt
        assert receipt["ledger_status"] == "peer_readback_verified"
        assert receipt["block_commit_verified"] is False
        path = tmp_path / "fabric_provenance_snapshot.json"
        data = json.loads(path.read_text())
        data["result"]["tx_id"] = "changed"
        path.write_text(json.dumps(data))
        with pytest.raises(ValueError):
            adapter.verify_export(record)


@pytest.mark.mcp_http
def test_camel_completes_with_fabric_provenance_contract(http_server, case, tmp_path):
    url = http_server(kind="fabric")
    case.package_version = "unknown"
    settings = BackendSettings(
        provenance=MCPSettings(url=url, expected_kind="real"),
        provenance_adapter="fabric-native-v1",
        fabric_provenance={"channel": "my-channel", "chaincode": "thesis-provenance"},
    )
    session = ArtifactSession(case, tmp_path / "workforce", mode="camel")
    model = ScriptedToolModel(session)
    with connect_backends(session, settings):
        result = run_camel(session, lambda: model)
        assert result.status == "insufficient_evidence"
        assert session.assert_complete().status == "insufficient_evidence"
        receipt = json.loads((session.output_dir / "provenance_receipt.json").read_text())
        assert receipt["backend"] == "mcp-fablo-provenance-v1"


def test_provenance_backend_requires_explicit_real_binding():
    with pytest.raises(ValueError, match="binding"):
        BackendSettings(provenance_adapter="fabric-native-v1")
    with pytest.raises(ValueError, match="native adapter"):
        BackendSettings(fabric_provenance={"channel": "channel", "chaincode": "cc"})
    assert set(fabric_provenance_contracts()) == {"record_provenance", "read_provenance"}
