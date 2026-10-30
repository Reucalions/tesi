"""Astensione esplicita, persistenza MCP e lettura RDF della provenienza."""

import json

import pytest
from rdflib import RDF, Dataset, Literal, Namespace, URIRef
from test_camel_integration import ScriptedToolModel

from services.strategic_gateway.server import ProvenanceStore, abstain_ranking
from thesis_agents.backends import BackendSettings, connect_backends
from thesis_agents.fixtures import fixture_candidates, run_fixtures
from thesis_agents.mcp.client import MCPClient, MCPError, digest
from thesis_agents.mcp.evidence_strategic_contracts import ReadProvenanceRequest
from thesis_agents.orchestration.artifacts import ArtifactSession
from thesis_agents.orchestration.workforce import run_camel
from thesis_agents.provenance import export_prov
from thesis_agents.schemas import ArgumentationGraph, ProvenanceRecord
from thesis_agents.tools.evidence_strategic_mcp import (
    EvidenceProvenanceTool,
    evidence_provenance_contracts,
)
from thesis_agents.tools.ranking_mock import build_graph


@pytest.fixture
def record(session):
    run_fixtures(session)
    return session.require("provenance", ProvenanceRecord)


def test_prov_export_is_readable_rdf_and_preserves_relations(record):
    document = export_prov(record)
    dataset = Dataset()
    dataset.parse(data=json.dumps(document), format="json-ld")
    prov = Namespace("http://www.w3.org/ns/prov#")
    vocab = Namespace("urn:tesi:vocab:")
    graph = dataset.graph(URIRef(document["@id"]))
    assert len(set(graph.subjects(RDF.type, prov.Entity))) == len(record.entities)
    assert len(set(graph.subjects(RDF.type, prov.Activity))) == len(record.activities)
    assert len(set(graph.subjects(RDF.type, prov.SoftwareAgent))) == len(record.agents)
    for entity in record.entities:
        node = URIRef(f"{document['@id']}:entity:{entity.id}")
        assert (node, vocab.sha256, Literal(entity.sha256)) in graph
    for activity in record.activities:
        node = URIRef(f"{document['@id']}:activity:{activity.id}")
        assert len(list(graph.objects(node, prov.used))) == len(activity.used)
        for generated in activity.generated:
            entity = URIRef(f"{document['@id']}:entity:{generated}")
            assert (entity, prov.wasGeneratedBy, node) in graph
            for used in activity.used:
                assert (
                    entity,
                    prov.wasDerivedFrom,
                    URIRef(f"{document['@id']}:entity:{used}"),
                ) in graph
    assert export_prov(record) == document


@pytest.mark.parametrize("fault", ["entity", "agent", "hash", "duplicate"])
def test_export_rejects_invalid_provenance(record, fault):
    if fault == "entity":
        record.activities[0].used.append("UNKNOWN")
    elif fault == "agent":
        record.activities[0].agent = "UNKNOWN"
    elif fault == "hash":
        record.entities[0].sha256 = "bad"
    else:
        record.entities.append(record.entities[0])
    with pytest.raises(ValueError):
        export_prov(record)


def test_store_is_immutable_idempotent_and_detects_tampering(tmp_path, record):
    store = ProvenanceStore(tmp_path / "archive")
    receipt = store.store(record)
    assert store.store(record) == receipt
    assert store.read(record.run_id).record == record
    changed = record.model_copy(update={"model": "changed"})
    with pytest.raises(ValueError, match="immutable"):
        store.store(changed)
    path = store.root / record.run_id / "provenance.jsonld"
    payload = json.loads(path.read_text())
    payload["tesi:ledgerStatus"] = "submitted"
    path.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match="differs"):
        store.read(record.run_id)


@pytest.mark.parametrize("run_id", [".", "..", "../escape"])
def test_store_rejects_directory_escape(run_id):
    with pytest.raises(ValueError):
        ReadProvenanceRequest(run_id=run_id)


def test_empty_strategy_gate_refuses_to_rank_real_candidates():
    empty = ArgumentationGraph(id="empty", arguments=[], relations=[])
    assert abstain_ranking(empty).ranking == []
    with pytest.raises(ValueError, match="BWAF"):
        abstain_ranking(build_graph(fixture_candidates(["CVE-2021-44228"]), "nonempty"))


@pytest.mark.parametrize("fault", ["request", "record_hash", "jsonld", "jsonld_hash", "ledger"])
def test_client_rejects_false_or_unbound_readback(tmp_path, record, fault):
    from types import SimpleNamespace

    from thesis_agents.mcp.contracts import ProvenanceRequest, ProvenanceResponse

    store = ProvenanceStore(tmp_path / "archive")

    class Client:
        settings = SimpleNamespace(expected_kind="real")

        def call_tool(self, name, arguments, parse):
            if name == "record_provenance":
                receipt = store.store(record)
                payload = ProvenanceResponse(
                    contract="provenance-record-v1",
                    backend_kind="real",
                    backend=receipt.backend,
                    result=receipt,
                    request_sha256=digest(ProvenanceRequest(record=record).model_dump(mode="json")),
                ).model_dump(mode="json")
            else:
                payload = store.read(record.run_id).model_dump(mode="json")
                if fault == "request":
                    payload["request_sha256"] = "0" * 64
                elif fault == "record_hash":
                    payload["record_sha256"] = "0" * 64
                elif fault == "jsonld":
                    payload["jsonld"] = {}
                    payload["jsonld_sha256"] = digest({})
                elif fault == "jsonld_hash":
                    payload["jsonld_sha256"] = "0" * 64
                else:
                    payload["ledger_status"] = "submitted"
            return parse(payload)

    client_dir = tmp_path / "client"
    client_dir.mkdir()
    with pytest.raises(ValueError):
        EvidenceProvenanceTool(Client(), client_dir).record_provenance(record)
    assert not list(client_dir.iterdir())


@pytest.mark.parametrize("field", ["ranking", "provenance", "semantic"])
def test_evidence_profile_rejects_incompatible_services(field):
    from pathlib import Path

    profile = json.loads(Path("config/backends.otel-apache-strategic.json").read_text())
    profile[field] = (
        {"transport": "mcp", "url": "http://127.0.0.1:1/mcp", "expected_kind": "real"}
        if field == "semantic"
        else {"transport": "local-mock"}
    )
    with pytest.raises(ValueError):
        BackendSettings.model_validate(profile)


@pytest.mark.mcp_http
def test_http_readback_proves_actual_storage_and_immutable_receipt(http_server, tmp_path, record):
    from thesis_agents.mcp.settings import MCPSettings

    directory = tmp_path / "store"
    url = http_server(kind="evidence", data_dir=directory)
    settings = MCPSettings(url=url, expected_kind="real")
    client_dir = tmp_path / "client"
    client_dir.mkdir()
    with MCPClient(settings, contracts=evidence_provenance_contracts()) as client:
        adapter = EvidenceProvenanceTool(client, client_dir)
        receipt = adapter.record_provenance(record)
        assert receipt["storage_kind"] == "artifact-files"
        assert receipt["ledger_status"] == "not_submitted"
        assert adapter.record_provenance(record) == receipt
        assert adapter.verify_export(record) == receipt
        stored = json.loads((directory / record.run_id / "record.json").read_text())
        assert digest(stored) == receipt["record_sha256"]
        assert json.loads((client_dir / "provenance.jsonld").read_text()) == export_prov(record)
        path = directory / record.run_id / "provenance.jsonld"
        path.write_text("{}")
        with pytest.raises(MCPError):
            adapter.record_provenance(record)


@pytest.mark.mcp_http
def test_camel_empty_path_completes_and_checks_local_export(http_server, case, tmp_path):
    case.package_version = "unknown"
    url = http_server(kind="evidence", data_dir=tmp_path / "archive")
    remote = {"transport": "mcp", "url": url, "expected_kind": "real"}
    profile = BackendSettings(
        strategic_adapter="empty-evidence-v1", ranking=remote, provenance=remote
    )
    session = ArtifactSession(case, tmp_path / "run", mode="camel", model="scripted-test-only")
    model = ScriptedToolModel(session)
    with connect_backends(session, profile):
        decision = run_camel(session, lambda: model)
    session.assert_complete()
    assert decision.status == "insufficient_evidence"
    assert any("No BWAF ranking or semantic" in c.text for c in decision.explanation_claims)
    events = [
        json.loads(line)
        for line in (session.output_dir / "mcp_events.jsonl").read_text().splitlines()
    ]
    calls = [e["tool"] for e in events if e["event"] == "tool_call"]
    assert calls == ["rank_graph", "record_provenance", "read_provenance"]
    (session.output_dir / "provenance.jsonld").write_text("{}")
    with pytest.raises(ValueError, match="differs"):
        session.assert_complete()
