"""Contratti e trasporto HTTP effettivo, con server separato e senza LLM/cloud."""

import asyncio
import json
import socket
import time

import pytest
from mcp.types import CallToolResult, TextContent

from thesis_agents.fixtures import fixture_evidence
from thesis_agents.mcp.client import MCPClient, MCPError, decode_result
from thesis_agents.mcp.settings import MCPSettings
from thesis_agents.orchestration.artifacts import ArtifactSession
from thesis_agents.schemas import SoftwareObservation
from thesis_agents.tools.vulnerability_mcp import MCPVulnerabilityTool, lookup_contracts
from thesis_agents.tools.vulnerability_mock import MockVulnerabilityTool

pytestmark = pytest.mark.mcp_http


def client(url, audit=None, timeout=5):
    return MCPClient(
        MCPSettings(url=url, expected_kind="mock", timeout_seconds=timeout),
        contracts=lookup_contracts(),
        audit=audit,
    )


@pytest.mark.parametrize("version", ["2.14.1", "9.9.9"])
def test_http_lookup_matches_local_backend_and_records_call(http_server, version):
    events = []
    software = SoftwareObservation(package="log4j-core", version=version, evidence_id="E1")
    connection = client(http_server(), events.append)
    with connection:
        result = MCPVulnerabilityTool(connection).lookup_vulnerabilities(software)
    assert result == MockVulnerabilityTool().lookup_vulnerabilities(software)
    assert events[0]["event"] == "connected"
    assert events[0]["server"]["name"] == "thesis-vulnerability-mock"
    assert events[1]["status"] == "validated"
    assert len(events[1]["input_sha256"]) == len(events[1]["response_sha256"]) == 64
    with pytest.raises(MCPError, match="non connesso"):
        MCPVulnerabilityTool(connection).lookup_vulnerabilities(software)


def test_sync_adapter_inside_async_loop_and_independent_runs(http_server):
    url = http_server()

    async def invoke(evidence_id):
        with client(url) as connection:
            result = MCPVulnerabilityTool(connection).lookup_vulnerabilities(
                SoftwareObservation(package="log4j-core", version="2.14.1", evidence_id=evidence_id)
            )
            return result.vulnerabilities[0].evidence_ids

    assert asyncio.run(invoke("E1")) == ["E1"]
    assert asyncio.run(invoke("E2")) == ["E2"]


@pytest.mark.parametrize("fault", ["missing", "bad-schema"])
def test_discovery_rejects_incompatible_server(http_server, fault):
    events = []
    with pytest.raises(MCPError, match="discovery"):
        with client(http_server(fault), events.append):
            pytest.fail("Incompatible server accepted")
    assert events[-1]["event"] == "connection_failed"


@pytest.mark.parametrize(
    "fault", ["tool-error", "wrong-evidence", "wrong-version", "wrong-kind", "disconnect"]
)
def test_bad_remote_result_cannot_publish_a_report(http_server, case, tmp_path, fault):
    events = []
    with client(http_server(fault), events.append) as connection:
        session = ArtifactSession(
            case,
            tmp_path / "run",
            mode="camel",
            vulnerability_tool=MCPVulnerabilityTool(connection),
        )
        evidence = fixture_evidence(session)
        session.publish_runtime_evidence(evidence.model_dump_json())
        with pytest.raises(MCPError):
            session.lookup_vulnerabilities()
        assert not (session.output_dir / "vulnerability_report.json").exists()
        assert session.get_context()["artifacts"]["runtime_evidence"] == evidence.model_dump(
            mode="json"
        )
    assert events[-1]["status"] == "failed"


def test_remote_timeout_is_bounded_and_closes_connection(http_server):
    events = []
    with client(http_server("timeout"), events.append, timeout=1) as connection:
        started = time.monotonic()
        with pytest.raises(MCPError):
            MCPVulnerabilityTool(connection).lookup_vulnerabilities(
                SoftwareObservation(package="log4j-core", version="2.14.1", evidence_id="E1")
            )
        assert time.monotonic() - started < 4
    assert connection._session is None
    assert events[-1]["status"] == "failed"


@pytest.mark.parametrize(
    "response",
    [
        CallToolResult(content=[], isError=True),
        CallToolResult(content=[TextContent(type="text", text="not json")]),
        CallToolResult(content=[TextContent(type="text", text="[]")]),
        CallToolResult(content=[TextContent(type="text", text='{"ok":false}')]),
        CallToolResult(content=[], structuredContent={"ok": False}),
    ],
)
def test_mcp_error_envelopes_are_not_domain_results(response):
    with pytest.raises(MCPError):
        decode_result(response)


def test_single_json_text_result_is_supported():
    payload = {"result": "example"}
    assert (
        decode_result(CallToolResult(content=[TextContent(type="text", text=json.dumps(payload))]))
        == payload
    )


@pytest.mark.parametrize(
    "url",
    [
        "file:///tmp/server",
        "http://user:secret@host/mcp",
        "https://host/mcp?token=secret",
        "https://host/mcp#fragment",
    ],
)
def test_config_accepts_only_http_endpoints_without_embedded_credentials(url):
    with pytest.raises(ValueError):
        MCPSettings(url=url, expected_kind="mock")


def test_real_camel_workforce_through_cli_uses_remote_lookup(http_server, tmp_path, monkeypatch):
    # Sostituiamo solo l'inferenza: CLI, CAMEL, tool, SDK MCP e HTTP sono effettivi.
    from test_camel_integration import ScriptedToolModel

    from thesis_agents.config import ModelSettings
    from thesis_agents.main import main
    from thesis_agents.orchestration.workforce import run_camel

    profile = tmp_path / "backends.json"
    profile.write_text(
        json.dumps(
            {"vulnerability": {"transport": "mcp", "url": http_server(), "expected_kind": "mock"}}
        )
    )
    models = []

    def scripted_run(session, factory, *, workflow):
        backend = ScriptedToolModel(session)
        models.append(backend)
        return run_camel(session, lambda: backend, workflow=workflow)

    monkeypatch.setattr("thesis_agents.orchestration.workforce.run_camel", scripted_run)
    monkeypatch.setattr(
        ModelSettings, "from_env", lambda: ModelSettings("scripted-test-only", "local")
    )
    output = tmp_path / "camel-run"
    assert main(["--backends", str(profile), "--output", str(output)]) == 0
    assert (
        json.loads((output / "final_decision.json").read_text())["selected_strategy_id"]
        == "S_UPGRADE"
    )
    events = [json.loads(line) for line in (output / "mcp_events.jsonl").read_text().splitlines()]
    calls = [event for event in events if event["event"] == "tool_call"]
    assert len(calls) == 1
    assert calls[0]["status"] == "validated"
    assert calls[0]["response_metadata"]["backend_kind"] == "mock"
    assert calls[0]["run_id"] == json.loads((output / "provenance.json").read_text())["run_id"]
    context = models[0].received_contexts["strategic"]["artifacts"]
    for artifact in ("runtime_evidence", "vulnerability_report", "candidate_strategies"):
        assert context[artifact] == json.loads((output / f"{artifact}.json").read_text())


def test_cli_rejects_remote_fixtures_before_creating_run(tmp_path):
    from thesis_agents.main import main

    profile = tmp_path / "backends.json"
    profile.write_text(
        json.dumps(
            {
                "vulnerability": {
                    "transport": "mcp",
                    "url": "http://127.0.0.1:1/mcp",
                    "expected_kind": "mock",
                }
            }
        )
    )
    output = tmp_path / "run"
    assert main(["--mode", "fixtures", "--backends", str(profile), "--output", str(output)]) == 1
    assert not output.exists()


def test_probe_entry_point_and_connection_failure(http_server, tmp_path, capsys):
    from thesis_agents.mcp.probe import main

    profile = tmp_path / "backends.json"
    profile.write_text(
        json.dumps(
            {"vulnerability": {"transport": "mcp", "url": http_server(), "expected_kind": "mock"}}
        )
    )
    assert main(["--backends", str(profile)]) == 0
    output = json.loads(capsys.readouterr().out)
    assert output["result"]["status"] == "matched"
    assert main(["--backends", str(profile), "--version", "9.9.9"]) == 0
    assert json.loads(capsys.readouterr().out)["result"]["status"] == "unsupported"
    # Porta riservata ma non in ascolto: errore certo, nessuna chiamata a un altro servizio.
    with socket.socket() as unavailable:
        unavailable.bind(("127.0.0.1", 0))
        config = json.loads(profile.read_text())
        config["vulnerability"]["url"] = f"http://127.0.0.1:{unavailable.getsockname()[1]}/mcp"
        config["vulnerability"]["timeout_seconds"] = 1
        profile.write_text(json.dumps(config))
        assert main(["--backends", str(profile)]) == 1
    captured = capsys.readouterr()
    assert not captured.out
    assert "Errore MCP" in captured.err


def test_missing_token_is_not_logged_or_replaced_by_local_mock(monkeypatch):
    monkeypatch.delenv("TEST_MCP_TOKEN", raising=False)
    events = []
    settings = MCPSettings(
        url="http://127.0.0.1:1/mcp", expected_kind="mock", token_env="TEST_MCP_TOKEN"
    )
    with pytest.raises(MCPError):
        with MCPClient(settings, contracts=lookup_contracts(), audit=events.append):
            pytest.fail("Missing credential accepted")
    assert events[-1]["event"] == "connection_failed"


def test_interrupted_call_releases_client_and_records_outcome(http_server):
    from thesis_agents.mcp.contracts import LOOKUP_TOOL

    events = []
    connection = client(http_server(), events.append)

    def interrupt_after_response(payload):
        raise KeyboardInterrupt

    with pytest.raises(KeyboardInterrupt), connection:
        connection.call_tool(
            LOOKUP_TOOL,
            {"software": {"package": "log4j-core", "version": "2.14.1", "evidence_id": "E1"}},
            interrupt_after_response,
        )
    assert connection._session is None
    assert events[-1]["status"] == "interrupted"


def test_explicit_local_profile_preserves_fixtures(tmp_path):
    from thesis_agents.main import main

    profile = tmp_path / "local.json"
    profile.write_text('{"vulnerability":{"transport":"local-mock"}}')
    output = tmp_path / "run"
    assert main(["--mode", "fixtures", "--backends", str(profile), "--output", str(output)]) == 0
    assert (output / "backends.json").exists()
    assert not (output / "mcp_events.jsonl").exists()
