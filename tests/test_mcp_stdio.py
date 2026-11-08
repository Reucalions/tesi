"""Trasporto stdio reale: processi, isolamento, CAMEL e teardown senza socket."""

import json
import os
import sys
import time
from pathlib import Path

import pytest

from thesis_agents.mcp.client import MCPClient, MCPError
from thesis_agents.mcp.settings import MCPStdioSettings
from thesis_agents.schemas import SoftwareObservation
from thesis_agents.tools.vulnerability_mcp import MCPVulnerabilityTool, lookup_contracts

ROOT = Path(__file__).resolve().parents[1]
SERVER = ROOT / "tests/support/mcp_stdio_server.py"


def stdio_settings(tmp_path, *, kind="lookup", fault="none", **kwargs):
    return MCPStdioSettings(
        command=sys.executable,
        args=(
            str(SERVER),
            "--pid-file",
            str(tmp_path / "child.pid"),
            "--kind",
            kind,
            "--fault",
            fault,
        ),
        cwd=str(ROOT),
        expected_kind="mock",
        timeout_seconds=5,
        **kwargs,
    )


def assert_child_stopped(path):
    pid = int(path.read_text())
    with pytest.raises(ProcessLookupError):
        os.kill(pid, 0)


def test_stdio_lookup_literal_arguments_environment_and_cleanup(tmp_path, monkeypatch):
    monkeypatch.setenv("PARENT_SENTINEL", "explicit-value")
    monkeypatch.setenv("UNMAPPED_SENTINEL", "unmapped-secret")
    shell_target = tmp_path / "shell-must-not-run"
    literal = f"$(touch {shell_target}); `touch {shell_target}`"
    settings = stdio_settings(tmp_path, env_from={"CHILD_SENTINEL": "PARENT_SENTINEL"})
    settings = settings.model_copy(
        update={
            "args": (
                *settings.args,
                "--state-file",
                str(tmp_path / "state.json"),
                "--literal",
                literal,
            )
        }
    )
    events = []
    with MCPClient(
        settings,
        contracts=lookup_contracts(),
        audit=events.append,
        stderr_path=tmp_path / "stderr.log",
    ) as connection:
        result = MCPVulnerabilityTool(connection).lookup_vulnerabilities(
            SoftwareObservation(package="log4j-core", version="2.14.1", evidence_id="E1")
        )
        assert result.vulnerabilities[0].evidence_ids == ["E1"]
        with pytest.raises(MCPError, match="non autorizzato"):
            connection.call_tool("unconfigured_tool", {}, lambda x: x)
    assert_child_stopped(tmp_path / "child.pid")
    assert json.loads((tmp_path / "state.json").read_text()) == {
        "literal": literal,
        "explicit": "explicit-value",
        "unmapped": None,
    }
    assert not shell_target.exists()
    assert "Fixture stderr" in (tmp_path / "stderr.log").read_text()
    assert events[-1]["status"] == "validated"
    audit = json.dumps(events)
    assert all(secret not in audit for secret in ("explicit-value", "unmapped-secret", literal))
    assert "explicit-value" not in settings.model_dump_json()


def test_stdio_startup_timeout_reaps_child(tmp_path):
    settings = stdio_settings(tmp_path, fault="startup-timeout").model_copy(
        update={"timeout_seconds": 0.5}
    )
    started = time.monotonic()
    with pytest.raises(MCPError, match="discovery"):
        with MCPClient(settings, contracts=lookup_contracts(), stderr_path=tmp_path / "stderr.log"):
            pytest.fail("Startup timeout ignored")
    assert time.monotonic() - started < 5
    assert_child_stopped(tmp_path / "child.pid")


def test_missing_environment_fails_before_starting_process(tmp_path):
    settings = stdio_settings(tmp_path, env_from={"TOKEN": "MISSING_STDIO_TEST_VARIABLE"})
    with pytest.raises(MCPError, match="discovery"):
        with MCPClient(settings, contracts=lookup_contracts()):
            pytest.fail("Missing environment accepted")
    assert not (tmp_path / "child.pid").exists()


@pytest.mark.parametrize(
    "invalid",
    [
        {"command": " "},
        {"command": "node\x00"},
        {"cwd": "relative/path"},
        {"args": ["bad\x00"]},
        {"env_from": {"TOKEN": "inline secret value"}},
        {"timeout_seconds": float("nan")},
        {"timeout_seconds": 0},
        {"env": {"TOKEN": "secret"}},
    ],
)
def test_invalid_stdio_settings_rejected(invalid):
    with pytest.raises(ValueError):
        MCPStdioSettings.model_validate({"command": "node", "expected_kind": "real", **invalid})


def test_camel_cli_uses_four_stdio_backends_without_local_fallback(tmp_path, monkeypatch):
    from test_camel_integration import ScriptedToolModel

    from thesis_agents.config import ModelSettings
    from thesis_agents.main import main
    from thesis_agents.orchestration.workforce import run_camel

    profile = {}
    for name in ("vulnerability", "ranking", "semantic", "provenance"):
        directory = tmp_path / name
        directory.mkdir()
        profile[name] = stdio_settings(
            directory, kind="lookup" if name == "vulnerability" else "strategic"
        ).model_dump(mode="json")
    profile_path = tmp_path / "backends.json"
    profile_path.write_text(json.dumps(profile))

    def forbidden_local(*args, **kwargs):
        pytest.fail("Local fallback executed in the agents process")

    for module, cls, method in [
        ("vulnerability", "MockVulnerabilityTool", "lookup_vulnerabilities"),
        ("ranking", "MockRankingTool", "rank_graph"),
        ("semantic", "MockSemanticTool", "validate_countermeasure"),
        ("provenance", "MockProvenanceTool", "record_provenance"),
    ]:
        monkeypatch.setattr(f"thesis_agents.tools.{module}_mock.{cls}.{method}", forbidden_local)

    def scripted_run(session, factory, *, workflow):
        model = ScriptedToolModel(session)
        return run_camel(session, lambda: model, workflow=workflow)

    monkeypatch.setattr("thesis_agents.orchestration.workforce.run_camel", scripted_run)
    monkeypatch.setattr(
        ModelSettings, "from_env", lambda: ModelSettings("scripted-test-only", "local")
    )
    output = tmp_path / "run"
    assert main(["--backends", str(profile_path), "--output", str(output)]) == 0
    assert (
        json.loads((output / "final_decision.json").read_text())["selected_strategy_id"]
        == "S_UPGRADE"
    )
    events = [json.loads(line) for line in (output / "mcp_events.jsonl").read_text().splitlines()]
    calls = [e for e in events if e["event"] == "tool_call"]
    assert [e["tool"] for e in calls] == [
        "lookup_vulnerabilities",
        "rank_graph",
        "validate_countermeasure",
        "record_provenance",
    ]
    assert all(e["status"] == "validated" for e in calls)
    assert len(list(output.glob("mcp-*.stderr.log"))) == 4
    assert (output / "provenance_receipt.json").exists()
    for name in profile:
        assert_child_stopped(tmp_path / name / "child.pid")


def test_stdio_profile_rejected_in_fixture_mode_before_output(tmp_path):
    from thesis_agents.main import main

    path = tmp_path / "backends.json"
    path.write_text(json.dumps({"vulnerability": stdio_settings(tmp_path).model_dump(mode="json")}))
    assert (
        main(["--mode", "fixtures", "--backends", str(path), "--output", str(tmp_path / "run")])
        == 1
    )
    assert not (tmp_path / "run").exists()
    assert not (tmp_path / "child.pid").exists()
