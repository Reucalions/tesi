"""CAMEL e trasporto MCP reali; servizio replay mock e inferenza SOLO programmata."""

import json

import pytest

from thesis_agents.backends import BackendSettings, connect_backends
from thesis_agents.fixtures import fixture_evidence
from thesis_agents.mcp.client import MCPError
from thesis_agents.orchestration.artifacts import ArtifactSession
from thesis_agents.orchestration.workforce import run_camel
from thesis_agents.schemas import ProvenanceRecord, VulnerabilityReport

pytestmark = pytest.mark.mcp_http


def profile(url, **kwargs):
    return BackendSettings(
        vulnerability_adapter="cve2owl-v1",
        vulnerability={"transport": "mcp", "url": url, "expected_kind": "mock"},
        **kwargs,
    )


@pytest.mark.parametrize(
    "package,version,lookup,decision",
    [
        ("log4j-core", "2.14.1", "ambiguous", "insufficient_evidence"),
        ("Apache Log4j2", "2.14.1", "not_evaluable", "insufficient_evidence"),
        ("zzzzcostathesisabsent9f832c", "1.0", "no_match", "insufficient_evidence"),
        ("Apache Log4j Core", "2.14.1", "matched", "selected"),
        ("Apache Log4j Core", "2.25.4", "no_findings", "no_findings"),
    ],
)
def test_cti_http_result_reaches_all_agents_without_replacing_runtime(
    http_server, case, tmp_path, monkeypatch, package, version, lookup, decision
):
    from test_camel_integration import ScriptedToolModel

    def no_local_lookup(*args):
        pytest.fail("CTI must use the remote tool; no local lookup fallback")

    monkeypatch.setattr(
        "thesis_agents.tools.vulnerability_mock.MockVulnerabilityTool.lookup_vulnerabilities",
        no_local_lookup,
    )
    case.package_name, case.package_version = package, version
    session = ArtifactSession(case, tmp_path / "run", mode="camel", model="scripted-test-only")
    model = ScriptedToolModel(session)
    with connect_backends(session, profile(http_server(kind="cti"))):
        result = run_camel(session, lambda: model)
    assert result.status == decision
    assert session.assert_complete() == result
    report = session.require("vulnerability_report", VulnerabilityReport)
    assert report.lookup_status == lookup
    context = model.received_contexts["strategic"]
    for name in ("runtime_evidence", "vulnerability_report", "candidate_strategies"):
        assert context["artifacts"][name] == json.loads(
            (session.output_dir / f"{name}.json").read_text()
        )
    assert context["artifact_producers"] == {
        "runtime_evidence": "TelemetryAgent",
        "vulnerability_report": "VulnerabilityAgent",
        "candidate_strategies": "CountermeasureAgent",
    }
    observed = context["artifacts"]["runtime_evidence"]["software"][0]
    assert (observed["package"], observed["version"]) == (package, version)
    assert report.cti.observed_software.model_dump(mode="json") == observed
    assert model.received_contexts["countermeasure"]["artifacts"]["vulnerability_report"] == (
        report.model_dump(mode="json")
    )
    if decision != "selected":
        assert context["artifacts"]["candidate_strategies"]["strategies"] == []
        assert "validate_countermeasure" not in model.tool_calls
        assert result.selected_strategy_id is None
    else:
        assert "CVSS unavailable" in result.explanation
    record = session.require("provenance", ProvenanceRecord)
    assert "cti_assessment" in {entity.id for entity in record.entities}
    assert "cti_assessment" in next(a for a in record.activities if a.id == "lookup").used
    events = [
        json.loads(line)
        for line in (session.output_dir / "mcp_events.jsonl").read_text().splitlines()
    ]
    calls = [event for event in events if event["event"] == "tool_call"]
    assert [(e["tool"], e["status"]) for e in calls] == [("assess_software", "validated")]

    # Anche dopo una decisione completa la sessione deve rilevare snapshot alterati.
    snapshot = session.output_dir / "cti_assessment.json"
    raw = json.loads(snapshot.read_text())
    raw["dataset"]["id"] = "altered-after-decision"
    snapshot.write_text(json.dumps(raw))
    with pytest.raises(ValueError, match="snapshot CTI"):
        session.assert_complete()


@pytest.mark.parametrize("fault", ["wrong-kind", "wrong-evidence", "dataset-pin"])
def test_failed_cti_validation_publishes_no_report_or_fallback(http_server, case, tmp_path, fault):
    url = http_server(kind="cti", fault="none" if fault == "dataset-pin" else fault)
    settings = profile(url, cti_dataset_sha256="0" * 64 if fault == "dataset-pin" else None)
    session = ArtifactSession(case, tmp_path / "run", mode="camel", model="scripted-test-only")
    session.publish_runtime_evidence(fixture_evidence(session).model_dump_json())
    with connect_backends(session, settings), pytest.raises(MCPError):
        session.lookup_vulnerabilities()
    assert session._lookup is None
    assert not (session.output_dir / "cti_assessment.json").exists()
    assert not (session.output_dir / "vulnerability_report.json").exists()
    events = [
        json.loads(line)
        for line in (session.output_dir / "mcp_events.jsonl").read_text().splitlines()
    ]
    assert next(e for e in events if e["event"] == "tool_call")["status"] == "failed"
