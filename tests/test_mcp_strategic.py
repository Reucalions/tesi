"""Tool strategici su HTTP reale; inferenza programmata, nessun backend live."""

import json
import socket
import sqlite3
from importlib.resources import files

import pytest

from thesis_agents.backends import BackendSettings, connect_backends
from thesis_agents.fixtures import fixture_candidates, fixture_evidence
from thesis_agents.mcp.client import MCPClient, MCPError, digest
from thesis_agents.mcp.contracts import ProvenanceReceipt
from thesis_agents.orchestration.artifacts import ArtifactSession
from thesis_agents.schemas import ProvenanceRecord
from thesis_agents.tools.strategic_mcp import MCPProvenanceTool, strategic_contracts

pytestmark = pytest.mark.mcp_http


def remote(url, **kwargs):
    return {"transport": "mcp", "url": url, "expected_kind": "mock", **kwargs}


def prepare(case, output):
    session = ArtifactSession(case, output, mode="camel", model="scripted-contract-test")
    session.publish_runtime_evidence(fixture_evidence(session).model_dump_json())
    report = session.lookup_vulnerabilities()
    session.publish_vulnerability_report(json.dumps(report))
    candidates = fixture_candidates([v["cve_id"] for v in report["vulnerabilities"]])
    session.publish_candidate_strategies(candidates.model_dump_json())
    session.build_argumentation_graph()
    return session


def events(session):
    return [
        json.loads(line)
        for line in (session.output_dir / "mcp_events.jsonl").read_text().splitlines()
    ]


@pytest.mark.parametrize(
    "scenario,status,selected,validations",
    [
        ("demo_01_nominal", "selected", "S_UPGRADE", 1),
        ("demo_02_no_maintenance", "selected", "S_ISOLATE", 2),
        ("demo_03_all_actions_prohibited", "no_valid_strategy", None, 4),
        ("demo_04_unsupported_lookup", "insufficient_evidence", None, 0),
    ],
)
def test_camel_cli_all_remote_four_cases_two_runs(
    http_server, tmp_path, monkeypatch, scenario, status, selected, validations
):
    from test_camel_integration import ScriptedToolModel

    from thesis_agents.config import ModelSettings
    from thesis_agents.main import main
    from thesis_agents.orchestration.workforce import run_camel

    store = tmp_path / "store"
    strategic_url = http_server(kind="strategic", data_dir=store)
    profile = tmp_path / "backends.json"
    profile.write_text(
        json.dumps(
            {
                "vulnerability": remote(http_server()),
                **{name: remote(strategic_url) for name in ("ranking", "semantic", "provenance")},
            }
        )
    )
    input_path = tmp_path / "input.json"
    input_path.write_text(files("thesis_agents").joinpath(f"data/{scenario}.json").read_text())
    runs = []

    def scripted_run(session, factory, *, workflow):
        model = ScriptedToolModel(session)
        runs.append((session, model))
        return run_camel(session, lambda: model, workflow=workflow)

    def forbidden_local_backend(*args, **kwargs):
        pytest.fail("Il run MCP ha eseguito il backend nel processo degli agenti")

    # I server sono processi indipendenti: questi stub colpiscono solo il client.
    for module, cls, method in [
        ("vulnerability", "MockVulnerabilityTool", "lookup_vulnerabilities"),
        ("ranking", "MockRankingTool", "rank_graph"),
        ("semantic", "MockSemanticTool", "validate_countermeasure"),
        ("provenance", "MockProvenanceTool", "record_provenance"),
    ]:
        monkeypatch.setattr(
            f"thesis_agents.tools.{module}_mock.{cls}.{method}", forbidden_local_backend
        )
    monkeypatch.setattr("thesis_agents.orchestration.workforce.run_camel", scripted_run)
    monkeypatch.setattr(
        ModelSettings, "from_env", lambda: ModelSettings("scripted-test-only", "local")
    )
    for repeat in (1, 2):
        output = tmp_path / f"run-{repeat}"
        assert (
            main(["--backends", str(profile), "--input", str(input_path), "--output", str(output)])
            == 0
        )
        session, model = runs[-1]
        decision = session.assert_complete()
        assert (decision.status, decision.selected_strategy_id) == (status, selected)
        calls = [e for e in events(session) if e["event"] == "tool_call"]
        assert [e["tool"] for e in calls] == [
            "lookup_vulnerabilities",
            "rank_graph",
            *(["validate_countermeasure"] * validations),
            "record_provenance",
        ]
        assert all(e["status"] == "validated" and e["run_id"] == session.run_id for e in calls)
        assert [e["backend_role"] for e in calls] == [
            "vulnerability",
            "ranking",
            *(["semantic"] * validations),
            "provenance",
        ]
        receipt = ProvenanceReceipt.model_validate_json(
            (output / "provenance_receipt.json").read_text()
        )
        record = session.require("provenance", ProvenanceRecord)
        assert record.backend == "mcp-provenance-mock-v1"
        assert receipt.record_sha256 == digest(record.model_dump(mode="json"))
        assert receipt.run_id == session.run_id
        # La ricevuta resta disponibile anche dopo la chiusura delle connessioni.
        assert session.record_provenance() == receipt.model_dump(mode="json")
        assert len([e for e in events(session) if e["event"] == "tool_call"]) == len(calls)
        context = model.received_contexts["strategic"]
        for name in ("runtime_evidence", "vulnerability_report", "candidate_strategies"):
            assert context["artifacts"][name] == json.loads((output / f"{name}.json").read_text())
        assert context["artifact_producers"] == {
            "runtime_evidence": "TelemetryAgent",
            "vulnerability_report": "VulnerabilityAgent",
            "candidate_strategies": "CountermeasureAgent",
        }
    assert runs[0][0].run_id != runs[1][0].run_id
    with sqlite3.connect(store / "provenance.sqlite3") as connection:
        assert connection.execute("SELECT count(*) FROM records").fetchone()[0] == 2


@pytest.mark.parametrize(
    "fault", ["wrong-id", "missing-strategy", "wrong-request", "wrong-kind", "wrong-backend"]
)
def test_ranking_rejects_unrelated_remote_result(http_server, tmp_path, case, fault):
    session = prepare(case, tmp_path / "run")
    settings = BackendSettings(ranking=remote(http_server(f"ranking:{fault}", kind="strategic")))
    with connect_backends(session, settings):
        with pytest.raises(MCPError):
            session.rank_graph()
        assert not (session.output_dir / "ranking.json").exists()
        assert "runtime_evidence" in session.get_context()["artifacts"]
    assert events(session)[-1]["status"] == "failed"


@pytest.mark.parametrize("fault", ["wrong-id", "wrong-request", "wrong-kind"])
def test_semantic_rejects_unrelated_remote_result(http_server, tmp_path, case, fault):
    session = prepare(case, tmp_path / "run")
    session.rank_graph()
    settings = BackendSettings(semantic=remote(http_server(f"semantic:{fault}", kind="strategic")))
    with connect_backends(session, settings):
        with pytest.raises(MCPError):
            session.validate_countermeasure("S_UPGRADE")
        assert not (session.output_dir / "semantic_validation.json").exists()
        with pytest.raises(ValueError):
            session.publish_final_decision("S_UPGRADE", "Unconfirmed validation")
    assert events(session)[-1]["status"] == "failed"


@pytest.mark.parametrize(
    "fault", ["wrong-id", "wrong-record", "wrong-request", "wrong-kind", "not-stored"]
)
def test_provenance_rejects_unconfirmed_receipt(http_server, tmp_path, case, fault):
    session = prepare(case, tmp_path / "run")
    session.rank_graph()
    session.validate_countermeasure("S_UPGRADE")
    session.publish_final_decision("S_UPGRADE", "Contract test")
    settings = BackendSettings(
        provenance=remote(http_server(f"provenance:{fault}", kind="strategic"))
    )
    with connect_backends(session, settings):
        with pytest.raises(MCPError):
            session.record_provenance()
        assert not (session.output_dir / "provenance_receipt.json").exists()
        assert not (session.output_dir / "provenance.json").exists()
        with pytest.raises(ValueError, match="provenance"):
            session.assert_complete()
    assert events(session)[-1]["status"] == "failed"


def test_remote_provenance_survives_new_server_and_detects_conflicts(http_server, tmp_path, case):
    from thesis_agents.mcp.settings import MCPSettings

    session = prepare(case, tmp_path / "source")
    session.rank_graph()
    session.validate_countermeasure("S_UPGRADE")
    session.publish_final_decision("S_UPGRADE", "Contract test")
    session.record_provenance()
    record = session.require("provenance", ProvenanceRecord)
    store = tmp_path / "store"
    receipts = []
    for repeat in (1, 2):
        settings = MCPSettings(**remote(http_server(kind="strategic", data_dir=store)))
        with MCPClient(settings, contracts=strategic_contracts("provenance")) as client:
            adapter = MCPProvenanceTool(client, tmp_path / f"receipt-{repeat}.json")
            receipts.append(adapter.record_provenance(record))
            assert adapter.record_provenance(record) == receipts[-1]
            if repeat == 2:
                altered = record.model_copy(update={"model": "different-model"})
                with pytest.raises(MCPError):
                    adapter.record_provenance(altered)
    assert receipts[0] == receipts[1]
    with sqlite3.connect(store / "provenance.sqlite3") as connection:
        rows = connection.execute("SELECT payload FROM records").fetchall()
        assert len(rows) == 1
        assert json.loads(rows[0][0]) == record.model_dump(mode="json")


def test_partial_startup_failure_closes_open_clients_without_installing_adapters(
    http_server, tmp_path, case, monkeypatch
):
    session = prepare(case, tmp_path / "run")
    original = session.ranking_tool
    opened = []
    enter = MCPClient.__enter__

    def capture(client):
        result = enter(client)
        opened.append(client)
        return result

    monkeypatch.setattr(MCPClient, "__enter__", capture)
    with socket.socket() as unavailable:
        unavailable.bind(("127.0.0.1", 0))
        settings = BackendSettings(
            ranking=remote(http_server(kind="strategic")),
            semantic=remote(
                f"http://127.0.0.1:{unavailable.getsockname()[1]}/mcp", timeout_seconds=1
            ),
        )
        with pytest.raises(MCPError), connect_backends(session, settings):
            pytest.fail("Workforce should not start with an unavailable backend")
    assert len(opened) == 1 and opened[0]._session is None
    assert session.ranking_tool is original
    assert events(session)[-1]["backend_role"] == "semantic"


@pytest.mark.parametrize("service", ["ranking", "semantic", "provenance"])
def test_fixture_cli_rejects_each_remote_strategic_backend(tmp_path, service):
    from thesis_agents.main import main

    profile = tmp_path / "backends.json"
    profile.write_text(json.dumps({service: remote("http://127.0.0.1:1/mcp")}))
    output = tmp_path / "run"
    assert main(["--mode", "fixtures", "--backends", str(profile), "--output", str(output)]) == 1
    assert not output.exists()


def test_probe_checks_all_contracts_without_writing_and_invokes_explicit_request(
    http_server, tmp_path, capsys, case
):
    from thesis_agents.mcp.probe import main

    store = tmp_path / "store"
    url = http_server(kind="strategic", data_dir=store)
    profile = tmp_path / "backends.json"
    profile.write_text(
        json.dumps({name: remote(url) for name in ("ranking", "semantic", "provenance")})
    )
    assert main(["--backends", str(profile), "--check-config"]) == 0
    result = json.loads(capsys.readouterr().out)
    assert {v["service"] for v in result["checked"]} == {"ranking", "semantic", "provenance"}
    assert all(e["event"] == "connected" for e in result["mcp_events"])
    with sqlite3.connect(store / "provenance.sqlite3") as connection:
        assert connection.execute("SELECT count(*) FROM records").fetchone()[0] == 0
    session = prepare(case, tmp_path / "source")
    graph = json.loads((session.output_dir / "argumentation_graph.json").read_text())
    request = tmp_path / "request.json"
    request.write_text(json.dumps({"graph": graph}))
    assert (
        main(["--backends", str(profile), "--service", "ranking", "--request", str(request)]) == 0
    )
    result = json.loads(capsys.readouterr().out)
    assert result["result"]["graph_id"] == graph["id"]
    assert result["result"]["ranking"][0]["strategy_id"] == "S_UPGRADE"
    context = session.get_context()["artifacts"]
    request.write_text(
        json.dumps(
            {
                "strategy": context["candidate_strategies"]["strategies"][0],
                "context": {
                    "evidence": context["runtime_evidence"],
                    "vulnerabilities": context["vulnerability_report"],
                    "available_capabilities": case.available_capabilities,
                    "prohibited_actions": case.prohibited_actions,
                },
            }
        )
    )
    assert (
        main(["--backends", str(profile), "--service", "semantic", "--request", str(request)]) == 0
    )
    assert json.loads(capsys.readouterr().out)["result"]["valid"] is True
    session.rank_graph()
    session.validate_countermeasure("S_UPGRADE")
    session.publish_final_decision("S_UPGRADE", "Contract test")
    session.record_provenance()
    request.write_text(
        json.dumps(
            {"record": session.require("provenance", ProvenanceRecord).model_dump(mode="json")}
        )
    )
    receipt = tmp_path / "receipt.json"
    assert (
        main(
            [
                "--backends",
                str(profile),
                "--service",
                "provenance",
                "--request",
                str(request),
                "--receipt",
                str(receipt),
            ]
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out)["result"] == json.loads(receipt.read_text())


def test_preflight_rejects_missing_strategic_tool(http_server, tmp_path, case):
    session = ArtifactSession(case, tmp_path / "run")
    settings = BackendSettings(ranking=remote(http_server("ranking:missing", kind="strategic")))
    with pytest.raises(MCPError, match="discovery"), connect_backends(session, settings):
        pytest.fail("Missing ranking tool should prevent agent startup")
    assert set(session.get_context()["artifacts"]) == {"input"}
    assert events(session)[-1]["event"] == "connection_failed"


def test_strategic_profile_keeps_input_lookup_local(http_server, tmp_path, case):
    session = prepare(case, tmp_path / "run")
    original = session.vulnerability_tool
    url = http_server(kind="strategic")
    settings = BackendSettings(
        **{name: remote(url) for name in ("ranking", "semantic", "provenance")}
    )
    with connect_backends(session, settings):
        session.rank_graph()
        session.validate_countermeasure("S_UPGRADE")
        session.publish_final_decision("S_UPGRADE", "Contract test")
        session.record_provenance()
    session.assert_complete()
    assert session.vulnerability_tool is original
    assert {e["backend_role"] for e in events(session)} == {"ranking", "semantic", "provenance"}
