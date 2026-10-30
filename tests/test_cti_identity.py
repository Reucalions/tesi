"""Contratto e probe del resolver: fixture sintetiche, nessun backend privato."""

import json

import pytest
import test_apache_recorded
import test_cti_probe

from thesis_agents.mcp import identity_probe
from thesis_agents.mcp.client import MCPError, digest
from thesis_agents.mcp.cti_contracts import AssessmentRequest, SoftwareQuery
from thesis_agents.mcp.identity_contracts import IdentityResolution
from thesis_agents.mcp.settings import MCPSettings

# Riusa le fixture sintetiche senza import che collidano con i parametri pytest.
apache_files = test_apache_recorded.apache_files
request_and_response = test_cti_probe.request_and_response


@pytest.fixture
def sample(apache_files, request_and_response):
    snapshot = test_apache_recorded.acquire(apache_files)
    request = identity_probe.request_from_snapshot(snapshot)
    query = SoftwareQuery(
        product="Apache HTTP Server",
        version="2.4.29",
        evidence_id=request.evidence.software.evidence_id,
    )
    _, raw = request_and_response
    raw["software"] = query.model_dump(mode="json")
    raw["request_sha256"] = digest(AssessmentRequest(software=query).model_dump(mode="json"))
    raw["matching"]["asset"] = {"product": query.product, "version": query.version}
    raw["matching"]["query"].update(
        product_terms=[query.product], normalized_product_terms=["apache http server"]
    )
    payload = IdentityResolution(
        backend_kind="mock",
        request_sha256=digest(request.model_dump(mode="json")),
        evidence=request.evidence,
        rule_sha256="a" * 64,
        resolver_sha256="b" * 64,
        status="no_match",
        normalized_query=query,
        group_id=None,
        selected_identity_ids=[],
        candidates=[],
        upstream_assessment=raw,
        limitations=["Synthetic empty CTI index"],
    ).model_dump(mode="json")
    return snapshot, request, payload


def test_normalization_preserves_recorded_evidence(sample):
    snapshot, request, payload = sample
    result = identity_probe.validate_identity(payload, request, "mock", "1" * 64)
    assert result.evidence.software.product == "Apache"
    assert result.evidence.software.version == "2.4.29"
    assert result.evidence.inventory_version == "2.4.29-1ubuntu4.21"
    assert result.normalized_query.product == "Apache HTTP Server"
    assert result.package_applicability == "not_assessed"
    assert request.evidence.telemetry_snapshot_sha256 == digest(snapshot.model_dump(mode="json"))
    assert request.evidence.original_log_sha256 == snapshot.observations[0].original_log.sha256


@pytest.mark.parametrize(
    "path,value",
    [
        (("request_sha256",), "0" * 64),
        (("evidence", "software", "evidence_id"), "other-source"),
        (("evidence", "inventory_version"), "2.4.29-invented"),
        (("evidence", "facts_sha256"), "0" * 64),
        (("backend_kind",), "real"),
        (("normalized_query", "version"), "2.4.29-1ubuntu4.21"),
        (("upstream_assessment", "request_sha256"), "0" * 64),
        (("upstream_assessment", "dataset", "kind"), "real"),
        (("package_applicability",), "vulnerable"),
        (("status",), "resolved"),
    ],
)
def test_inconsistent_or_unjustified_claim_rejected(sample, path, value):
    _, request, payload = sample
    target = payload
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    with pytest.raises(ValueError):
        identity_probe.validate_identity(payload, request, "mock")


def test_dataset_revision_is_checked(sample):
    _, request, payload = sample
    with pytest.raises(ValueError, match="dataset differs"):
        identity_probe.validate_identity(payload, request, "mock", "0" * 64)


def test_probe_preserves_input_and_failure_audit(sample, tmp_path, monkeypatch):
    snapshot, request, payload = sample
    source = tmp_path / "snapshot.json"
    source.write_text(snapshot.model_dump_json(indent=2))
    fail = False

    class Connection:
        def __init__(self, settings, *, contracts, audit):
            self.audit = audit

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def call_tool(self, name, arguments, parse):
            assert name == "resolve_software_identity"
            assert arguments == request.model_dump(mode="json")
            self.audit({"event": "synthetic-client-test"})
            if fail:
                raise MCPError("Synthetic transport failure")
            return parse(payload)

    monkeypatch.setattr(identity_probe, "MCPClient", Connection)
    settings = MCPSettings(url="http://127.0.0.1:8005/mcp", expected_kind="mock")
    output = tmp_path / "probe"
    identity_probe.run_probe(settings, source, output)
    assert (output / "telemetry_snapshot.json").read_bytes() == source.read_bytes()
    summary = json.loads((output / "summary.json").read_text())
    assert summary["status"] == "validated" and summary["workforce_run"] is False
    with pytest.raises(FileExistsError):
        identity_probe.run_probe(settings, source, output)
    fail = True
    output = tmp_path / "failed"
    with pytest.raises(MCPError):
        identity_probe.run_probe(settings, source, output)
    assert not (output / "identity_resolution.json").exists()
    assert json.loads((output / "summary.json").read_text())["status"] == "failed"
    assert json.loads((output / "audit.json").read_text())
