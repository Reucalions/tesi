"""Ubuntu adapter, immutable publication and CAMEL handoff using synthetic contracts."""

import json
from types import SimpleNamespace

import pytest
import test_ubuntu_probe
from test_camel_integration import ScriptedToolModel

from thesis_agents.backends import BackendSettings
from thesis_agents.mcp.client import digest
from thesis_agents.mcp.ubuntu_contracts import VERDICTS, PackageAssessment
from thesis_agents.mcp.v1_domain import legacy_payload
from thesis_agents.orchestration.artifacts import ArtifactSession
from thesis_agents.orchestration.workforce import run_camel
from thesis_agents.schemas import VulnerabilityReport
from thesis_agents.tools.telemetry_http import evidence_from_snapshot
from thesis_agents.tools.ubuntu_mcp import UbuntuVulnerabilityTool, map_ubuntu_assessment

apache_files = test_ubuntu_probe.apache_files
request_and_response = test_ubuntu_probe.request_and_response
sample = test_ubuntu_probe.sample
v2_sample = test_ubuntu_probe.v2_sample
package_sample = test_ubuntu_probe.package_sample


@pytest.fixture
def resolved_package(package_sample):
    snapshot, request, payload = package_sample
    identity = payload["identity_resolution"]
    ids = [f"CVE-2099-{index:04d}" for index in range(1, 5)]
    identity.update(
        status="resolved",
        group_id="apache:http_server",
        selected_identity_ids=["synthetic:apache"],
        candidates=[
            dict(
                canonical_id="synthetic:apache",
                disposition="equivalent",
                reason="Synthetic reviewed identity",
                entry_count=4,
                cve_ids=ids,
                references=["https://example.invalid/identity"],
            )
        ],
    )
    identity["search"]["coverage"].update(generated_candidates=1, returned_candidates=1)
    identity["search"]["matching"].update(
        status="matched",
        matches=[
            dict(
                canonical_id="synthetic:apache",
                vendor="apache",
                product="http_server",
                normalized_vendor="apache",
                normalized_product="http server",
                affected_count=4,
                confidence="high",
                score=1.0,
                evidence=["sqlite_token"],
                affected_entries=[
                    dict(
                        affected_product_id=i,
                        cve_id=cve,
                        affected_iri=f"urn:test:{i}",
                        json_path=f"/test/{i}",
                        vendor="apache",
                        product="http_server",
                    )
                    for i, cve in enumerate(ids)
                ],
            )
        ],
    )
    results = []
    for cve, verdict in zip(ids, VERDICTS, strict=True):
        status = {
            "fixed": "released",
            "not_affected": "not-affected",
            "potentially_affected": "released",
            "unknown": None,
        }[verdict]
        boundary = (
            "2.4.29-1ubuntu4.21"
            if verdict == "fixed"
            else "2.4.29-1ubuntu4.22"
            if verdict == "potentially_affected"
            else None
        )
        results.append(
            dict(
                cve_id=cve,
                identity_ids=["synthetic:apache"],
                verdict=verdict,
                reason="Synthetic package status",
                source=dict(url="https://example.invalid/cve", sha256="d" * 64),
                ubuntu_statuses=[
                    dict(
                        pointer="/packages/0/statuses/0",
                        status=status,
                        description=boundary,
                        pocket=None,
                    )
                ]
                if status
                else [],
                ubuntu_published=None,
                ubuntu_updated_at=None,
                version_boundary=boundary,
                comparison="eq" if verdict == "fixed" else "lt" if boundary else None,
            )
        )
    payload.update(status="assessed", results=results, counts=dict.fromkeys(VERDICTS, 1))
    return snapshot, request, PackageAssessment.model_validate(payload)


class Client:
    settings = SimpleNamespace(expected_kind="mock")

    def __init__(self, payload):
        self.payload, self.calls = payload, []

    def call_tool(self, name, arguments, parse):
        self.calls.append((name, arguments))
        return parse(self.payload)


def make_session(tmp_path, apache_files, sample):
    snapshot, _, response = sample
    client = Client(response.model_dump(mode="json"))

    class Source:
        def collect(self, query):
            assert query == snapshot.query
            return snapshot

    session = ArtifactSession(
        apache_files[3], tmp_path / "run", telemetry_tool=Source(), model="scripted-test-only"
    )
    session.vulnerability_tool = UbuntuVulnerabilityTool(
        client, session.output_dir, dataset_sha256="1" * 64, sources_sha256="c" * 64
    )
    return session, client


def test_mapping_preserves_four_groups_without_runtime_findings(resolved_package):
    snapshot, _, response = resolved_package
    result = map_ubuntu_assessment(response, snapshot)
    assert result.status == "not_evaluable" and result.vulnerabilities == [] and result.cti is None
    package = result.package_assessment
    assert package.counts == dict.fromkeys(VERDICTS, 1)
    assert package.identity_status == "resolved" and package.search_complete
    assert package.response_sha256 == digest(response.model_dump(mode="json"))
    assert package.observed_software == evidence_from_snapshot(snapshot).software[0]
    assert package.historical_runtime_state == "not_established"
    assert package.cve_ids_by_verdict["potentially_affected"] == ["CVE-2099-0003"]


def test_legacy_wire_only_accepts_absent_package_context(resolved_package):
    original = {"asset_id": "synthetic", "lookup_status": "unsupported", "vulnerabilities": []}
    assert legacy_payload({**original, "cti": None, "package_assessment": None}) == original
    snapshot, _, response = resolved_package
    result = map_ubuntu_assessment(response, snapshot)
    with pytest.raises(ValueError, match="Ubuntu"):
        legacy_payload({**original, "package_assessment": result.package_assessment.model_dump()})


def test_unresolved_identity_is_preserved(package_sample):
    snapshot, _, payload = package_sample
    result = map_ubuntu_assessment(PackageAssessment.model_validate(payload), snapshot)
    assert result.status == "no_match"
    assert result.package_assessment.package_status == "not_assessed"


def test_all_fixed_packages_still_do_not_attest_runtime(resolved_package):
    snapshot, _, response = resolved_package
    payload = response.model_dump(mode="json")
    fixed = payload["results"][0]
    for result in payload["results"]:
        for key in ("verdict", "ubuntu_statuses", "version_boundary", "comparison"):
            result[key] = fixed[key]
    payload["counts"] = {v: 4 if v == "fixed" else 0 for v in VERDICTS}
    mapped = map_ubuntu_assessment(PackageAssessment.model_validate(payload), snapshot)
    assert mapped.status == "not_evaluable" and mapped.vulnerabilities == []


def test_adapter_rejects_changed_evidence_and_snapshot_rewrite(tmp_path, resolved_package):
    snapshot, _, response = resolved_package
    client = Client(response.model_dump(mode="json"))
    adapter = UbuntuVulnerabilityTool(
        client, tmp_path, dataset_sha256="1" * 64, sources_sha256="c" * 64
    )
    evidence = evidence_from_snapshot(snapshot)
    changed = evidence.model_copy(update={"observations": ["Altered"]})
    with pytest.raises(ValueError, match="exact published"):
        adapter.lookup_runtime_vulnerabilities(changed, snapshot)
    assert client.calls == []
    adapter.lookup_runtime_vulnerabilities(evidence, snapshot)
    original = (tmp_path / "ubuntu_package_assessment.json").read_bytes()
    client.payload["limitations"].append("Changed remote response")
    with pytest.raises(ValueError, match="immutable"):
        adapter.lookup_runtime_vulnerabilities(evidence, snapshot)
    assert (tmp_path / "ubuntu_package_assessment.json").read_bytes() == original


def test_camel_handoff_provenance_and_cached_lookup(tmp_path, apache_files, resolved_package):
    session, client = make_session(tmp_path, apache_files, resolved_package)
    model = ScriptedToolModel(session)
    decision = run_camel(session, lambda: model)
    session.assert_complete()
    assert decision.status == "insufficient_evidence"
    report = session.require("vulnerability_report", VulnerabilityReport)
    for role in ("countermeasure", "strategic"):
        context = model.received_contexts[role]
        assert context["artifacts"]["vulnerability_report"] == report.model_dump(mode="json")
        assert context["artifact_producers"]["runtime_evidence"] == "TelemetryAgent"
    assert session.get_context()["artifacts"]["candidate_strategies"]["strategies"] == []
    session.lookup_vulnerabilities()
    assert len(client.calls) == 1
    provenance = json.loads((session.output_dir / "provenance.json").read_text())
    assert "ubuntu_package_assessment" in {e["id"] for e in provenance["entities"]}
    lookup = next(a for a in provenance["activities"] if a["id"] == "lookup")
    assert "ubuntu_package_assessment" in lookup["used"]
    assert any("potentially_affected=1" in c.text for c in decision.explanation_claims)


@pytest.mark.parametrize("field", ["counts", "lookup_status", "snapshot"])
def test_report_or_snapshot_tampering_rejected(tmp_path, apache_files, resolved_package, field):
    session, _ = make_session(tmp_path, apache_files, resolved_package)
    session.publish_runtime_evidence(json.dumps(session.collect_runtime_evidence()))
    payload = session.lookup_vulnerabilities()
    if field == "counts":
        payload["package_assessment"]["counts"]["fixed"] += 1
    elif field == "lookup_status":
        payload["lookup_status"] = "matched"
    else:
        path = session.output_dir / "ubuntu_package_assessment.json"
        response = json.loads(path.read_text())
        response["limitations"].append("Altered after lookup")
        path.write_text(json.dumps(response))
    with pytest.raises(ValueError):
        session.publish_vulnerability_report(json.dumps(payload))


@pytest.mark.parametrize("field", ["source_manifest_sha256", "request_sha256"])
def test_wrong_source_or_request_never_saved(tmp_path, resolved_package, field):
    snapshot, _, response = resolved_package
    payload = response.model_dump(mode="json")
    payload[field] = "0" * 64
    adapter = UbuntuVulnerabilityTool(
        Client(payload), tmp_path, dataset_sha256="1" * 64, sources_sha256="c" * 64
    )
    with pytest.raises(ValueError):
        adapter.lookup_runtime_vulnerabilities(evidence_from_snapshot(snapshot), snapshot)
    assert not (tmp_path / "ubuntu_package_assessment.json").exists()


@pytest.mark.parametrize(
    "change",
    [
        dict(cti_dataset_sha256=None),
        dict(ubuntu_sources_sha256=None),
        dict(telemetry={"transport": "static"}),
        dict(vulnerability={"transport": "local-mock"}),
        dict(vulnerability_adapter="cve2owl-v1"),
    ],
)
def test_ubuntu_profile_requires_supported_source_and_pins(change):
    from pathlib import Path

    profile = json.loads(Path("config/backends.otel-apache-ubuntu.json").read_text())
    profile.update(change)
    with pytest.raises(ValueError):
        BackendSettings.model_validate(profile)
