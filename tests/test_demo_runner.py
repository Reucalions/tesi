"""Runner: processi isolati, audit dei file e fallimenti conservati nel riepilogo."""

import json
import subprocess
import sys

import pytest

from thesis_agents import demo
from thesis_agents.demo_audit import _audit_messages, audit_run
from thesis_agents.fixtures import run_fixtures
from thesis_agents.orchestration.artifacts import (
    ARTIFACT_PRODUCERS,
    ARTIFACT_SCHEMAS,
    ArtifactSession,
)
from thesis_agents.schemas import StaticTelemetry


def test_fixture_matrix_no_network_and_no_overwrite(tmp_path, monkeypatch):
    def no_network(_):
        pytest.fail("La matrice fixture non deve contattare Ollama")

    monkeypatch.setattr(demo, "local_model_info", no_network)
    batch = tmp_path / "matrix"
    args = ["--mode", "fixtures", "--repetitions", "1", "--output", str(batch)]
    assert demo.main(args) == 0
    summary = json.loads((batch / "summary.json").read_text())
    assert summary["state"] == "passed"
    assert summary["verified_runs"] == summary["planned_runs"] == 4
    assert [r["audit"]["decision_status"] for r in summary["runs"]] == [
        "selected",
        "selected",
        "no_valid_strategy",
        "insufficient_evidence",
    ]
    assert summary["runs"][1]["audit"]["fallback_observed"]
    manifest = json.loads((batch / "manifest.json").read_text())
    assert manifest["model"] is None and manifest["source_hashes"] and manifest["input_hashes"]
    saved = {p: p.read_bytes() for p in batch.rglob("*") if p.is_file()}
    assert demo.main(args) == 1
    assert saved == {p: p.read_bytes() for p in saved}


def test_local_environment_overrides_paid_configuration(tmp_path, monkeypatch):
    monkeypatch.setenv("LLM_API_KEY", "do-not-use")
    monkeypatch.setenv("OPENAI_API_KEY", "do-not-use")
    monkeypatch.setenv("LLM_BASE_URL", "https://example.invalid/paid")
    env = demo.child_environment(tmp_path, "tesi-qwen3:4b")
    assert env["LLM_BASE_URL"] == "http://localhost:11434/v1"
    assert env["LLM_API_KEY"] == env["OPENAI_API_KEY"] == "local"
    assert env["LLM_MODEL"] == "tesi-qwen3:4b"


def test_timeout_terminates_child_and_preserves_partial_log(tmp_path):
    result = demo.execute(
        [sys.executable, "-u", "-c", "import time; print('started'); time.sleep(30)"],
        run=tmp_path,
        env=demo.child_environment(tmp_path, "unused"),
        timeout=1,
    )
    assert result["execution_status"] == "timeout" and result["exit_code"] == 124
    assert "started" in (tmp_path / "run.log").read_text()


def test_execute_records_nonzero_and_interrupt(tmp_path, monkeypatch):
    result = demo.execute(
        [sys.executable, "-c", "raise SystemExit(7)"], run=tmp_path, env={}, timeout=3
    )
    assert result["execution_status"] == "failed" and result["exit_code"] == 7

    def interrupted(*args, **kwargs):
        raise KeyboardInterrupt

    monkeypatch.setattr(subprocess, "run", interrupted)
    result = demo.execute(["unused"], run=tmp_path, env={}, timeout=3)
    assert result["execution_status"] == "interrupted" and result["exit_code"] == 130


def test_batch_continues_after_failed_run(tmp_path, monkeypatch):
    real_execute = demo.execute
    calls = 0

    def first_timeout(*args, **kwargs):
        nonlocal calls
        calls += 1
        if calls == 1:
            return {"exit_code": 124, "execution_status": "timeout", "elapsed_seconds": 1}
        return real_execute(*args, **kwargs)

    monkeypatch.setattr(demo, "execute", first_timeout)
    batch = tmp_path / "matrix"
    assert demo.main(["--mode", "fixtures", "--repetitions", "1", "--output", str(batch)]) == 1
    summary = json.loads((batch / "summary.json").read_text())
    assert summary["state"] == "failed" and summary["finished_runs"] == 4
    assert summary["verified_runs"] == 3
    assert summary["runs"][0]["execution_status"] == "timeout"
    assert "decision_status" not in summary["runs"][0]["audit"]
    assert summary["runs"][0]["audit"]["errors"]


def test_changed_sources_stop_matrix(tmp_path, monkeypatch):
    calls = 0

    def changed():
        nonlocal calls
        calls += 1
        return {"source": "before" if calls == 1 else "after"}

    monkeypatch.setattr(demo, "source_hashes", changed)
    batch = tmp_path / "matrix"
    assert demo.main(["--mode", "fixtures", "--output", str(batch)]) == 1
    summary = json.loads((batch / "summary.json").read_text())
    assert summary["finished_runs"] == 0 and summary["errors"]


@pytest.mark.parametrize("corruption", ["hash", "empty_entities", "ranking", "explanation"])
def test_audit_detects_valid_json_corruption_without_rewriting(case, tmp_path, corruption):
    run_fixtures(ArtifactSession(case, tmp_path / "artifacts", mode="fixtures"))
    artifact = {
        "hash": "provenance",
        "empty_entities": "provenance",
        "ranking": "ranking",
        "explanation": "final_decision",
    }[corruption]
    path = tmp_path / "artifacts" / f"{artifact}.json"
    value = json.loads(path.read_text())
    if corruption == "hash":
        value["entities"][0]["sha256"] = "0" * 64
    elif corruption == "empty_entities":
        value["entities"] = []
    elif corruption == "ranking":
        value["ranking"][0]["score"] = 1.0
    else:
        value["explanation_claims"][0]["text"] = "Unfounded assertion"
        value["explanation"] = "\n\n".join(c["text"] for c in value["explanation_claims"])
    path.write_text(json.dumps(value))
    before = {p: p.read_bytes() for p in (tmp_path / "artifacts").iterdir()}
    result = audit_run(tmp_path, case, mode="fixtures", model=None)
    assert not result["passed"]
    assert all(v == "valid" for v in result["artifacts"].values())
    assert before == {p: p.read_bytes() for p in before}


@pytest.mark.parametrize("serialize", [json.dumps, repr])
def test_sdk_audit_requires_actual_matching_context_and_decision(case, tmp_path, serialize):
    run_fixtures(ArtifactSession(case, tmp_path / "artifacts", mode="fixtures"))
    values = {
        name: schema.model_validate_json((tmp_path / "artifacts" / f"{name}.json").read_text())
        for name, schema in {"input": StaticTelemetry, **ARTIFACT_SCHEMAS}.items()
    }
    context = {
        "artifacts": {name: values[name].model_dump(mode="json") for name in ARTIFACT_PRODUCERS},
        "artifact_producers": ARTIFACT_PRODUCERS,
    }
    logs = tmp_path / "llm"
    logs.mkdir()
    for role in (*ARTIFACT_PRODUCERS.values(), "StrategicAgent"):
        messages = [{"role": "system", "content": f"You are {role}."}]
        if role == "StrategicAgent":
            messages += [
                {"role": "tool", "content": serialize(context)},
                {"role": "tool", "content": serialize(values["final_decision"].model_dump())},
            ]
        (logs / f"{role}.json").write_text(json.dumps({"request": {"messages": messages}}))
    result = {"errors": [], "checks": {}}
    _audit_messages(tmp_path, values, result)
    assert not result["errors"] and all(result["checks"].values())
    context["artifacts"]["runtime_evidence"]["service_name"] = "different-service"
    messages[1]["content"] = serialize(context)
    (logs / "StrategicAgent.json").write_text(json.dumps({"request": {"messages": messages}}))
    _audit_messages(tmp_path, values, result)
    assert not result["checks"]["strategic_inputs_delivered"]
