"""Pending checks retain evidence scope and never enter remediation ranking."""

import json

import pytest
import test_ubuntu_adapter
from test_camel_integration import ScriptedToolModel

from thesis_agents.fixtures import fixture_candidates, fixture_evidence
from thesis_agents.mcp.client import digest
from thesis_agents.orchestration.workforce import run_camel
from thesis_agents.schemas import CandidateStrategies, VulnerabilityReport
from thesis_agents.tools.package_verification import package_verification_context
from thesis_agents.tools.telemetry_http import evidence_from_snapshot
from thesis_agents.tools.ubuntu_mcp import map_ubuntu_assessment

apache_files = test_ubuntu_adapter.apache_files
request_and_response = test_ubuntu_adapter.request_and_response
sample = test_ubuntu_adapter.sample
v2_sample = test_ubuntu_adapter.v2_sample
package_sample = test_ubuntu_adapter.package_sample
resolved_package = test_ubuntu_adapter.resolved_package


@pytest.fixture
def prepared(tmp_path, apache_files, resolved_package):
    session, _ = test_ubuntu_adapter.make_session(
        tmp_path / "package", apache_files, resolved_package
    )
    session.publish_runtime_evidence(json.dumps(session.collect_runtime_evidence()))
    session.publish_vulnerability_report(json.dumps(session.lookup_vulnerabilities()))
    return session


def test_requests_cover_pending_cves_and_resolve_sources(prepared):
    context = prepared.prepare_package_verification()
    requests = context["verification_requests"]
    assert [r["kind"] for r in requests] == [
        "historical_runtime_state",
        "runtime_conditions",
        "ubuntu_status",
        "upgrade_compatibility",
    ]
    assert [len(r["cve_ids"]) for r in requests] == [2, 1, 1, 1]
    report = prepared.get_context()["artifacts"]["vulnerability_report"]
    package = report["package_assessment"]
    pending = set(
        package["cve_ids_by_verdict"]["potentially_affected"]
        + package["cve_ids_by_verdict"]["unknown"]
    )
    assert {cve for r in requests for cve in r["cve_ids"]} == pending
    assert context["vulnerability_report_sha256"] == digest(report)
    for request in requests:
        assert request["status"] == "pending" and request["purpose"] == "evidence_collection_only"
        assert request["source_artifact"] == "vulnerability_report"
        for pointer in request["source_pointers"]:
            value = report
            for token in pointer.split("/")[1:]:
                value = value[token]


def test_preparation_required_and_retry_preserves_files(prepared):
    with pytest.raises(ValueError, match="prepare_package_verification"):
        prepared.publish_candidate_strategies('{"strategies": []}')
    first = prepared.prepare_package_verification()
    path = prepared.output_dir / "package_verification_context.json"
    content = path.read_bytes()
    assert prepared.prepare_package_verification() == first
    assert path.read_bytes() == content
    first["verification_requests"].clear()
    assert prepared.prepare_package_verification()["verification_requests"]


@pytest.mark.parametrize(
    "fault", ["omitted", "unknown_cve", "fixed_cve", "executed", "target", "source"]
)
def test_agent_cannot_drop_or_invent_requests(prepared, fault):
    context = prepared.prepare_package_verification()
    requests = context["verification_requests"]
    if fault == "omitted":
        requests.pop()
    elif fault in ("unknown_cve", "fixed_cve"):
        requests[1]["cve_ids"] = ["CVE-2099-9999" if fault == "unknown_cve" else "CVE-2099-0001"]
    elif fault == "executed":
        requests[0]["status"] = "completed"
    elif fault == "target":
        requests[3]["upgrade_target"] = "invented-version"
    else:
        requests[0]["source_pointers"] = ["/invented"]
    with pytest.raises(ValueError):
        prepared.publish_candidate_strategies(
            json.dumps({"strategies": [], "verification_requests": requests})
        )
    assert not (prepared.output_dir / "candidate_strategies.json").exists()


@pytest.mark.parametrize("checkpoint", ["publish", "context", "complete"])
def test_changed_context_is_detected(prepared, checkpoint):
    context = prepared.prepare_package_verification()
    if checkpoint == "complete":
        run_camel(prepared, lambda: ScriptedToolModel(prepared))
    context["limitations"].append("Changed after preparation")
    (prepared.output_dir / "package_verification_context.json").write_text(json.dumps(context))
    with pytest.raises(ValueError, match="differs from validated"):
        if checkpoint == "publish":
            prepared.publish_candidate_strategies(
                json.dumps(
                    {"strategies": [], "verification_requests": context["verification_requests"]}
                )
            )
        elif checkpoint == "context":
            prepared.get_context()
        else:
            prepared.assert_complete()


def test_legacy_output_unchanged_and_requests_rejected(session, prepared):
    session.publish_runtime_evidence(fixture_evidence(session).model_dump_json())
    report = session.lookup_vulnerabilities()
    session.publish_vulnerability_report(json.dumps(report))
    candidates = fixture_candidates([v["cve_id"] for v in report["vulnerabilities"]])
    payload = candidates.model_dump(mode="json")
    assert "verification_requests" not in payload
    assert "package_verification" not in session.get_context().get("external_inputs", {})
    payload["verification_requests"] = prepared.prepare_package_verification()[
        "verification_requests"
    ]
    with pytest.raises(ValueError, match="require Ubuntu"):
        session.publish_candidate_strategies(json.dumps(payload))


def test_camel_handoff_keeps_requests_out_of_graph_and_records_provenance(prepared):
    model = ScriptedToolModel(prepared)
    decision = run_camel(prepared, lambda: model)
    prepared.assert_complete()
    candidates = prepared.require("candidate_strategies", CandidateStrategies)
    assert len(candidates.verification_requests) == 4 and candidates.strategies == []
    assert decision.ranking == [] and decision.selected_strategy_id is None
    assert decision.status == "insufficient_evidence"
    context = model.received_contexts["strategic"]
    assert context["artifacts"]["candidate_strategies"] == candidates.model_dump(mode="json")
    assert any("pending evidence requests" in c.text for c in decision.explanation_claims)
    provenance = json.loads((prepared.output_dir / "provenance.json").read_text())
    assert "package_verification_context" in {e["id"] for e in provenance["entities"]}
    stage = next(a for a in provenance["activities"] if a["id"] == "prepare_package_verification")
    assert stage["agent"] == "CountermeasureAgent"
    assert "ubuntu_package_assessment" in stage["used"]


def test_no_match_does_not_invent_a_verification_set(package_sample):
    from thesis_agents.mcp.ubuntu_contracts import PackageAssessment

    snapshot, _, payload = package_sample
    result = map_ubuntu_assessment(PackageAssessment.model_validate(payload), snapshot)
    evidence = evidence_from_snapshot(snapshot)
    report = VulnerabilityReport(
        asset_id=evidence.service_name,
        lookup_status=result.status,
        vulnerabilities=[],
        package_assessment=result.package_assessment,
    )
    assert package_verification_context(evidence, report).verification_requests == []
