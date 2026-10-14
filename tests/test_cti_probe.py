"""Controlli sul confine del nuovo servizio; nessun import della pipeline esterna."""

import json

import pytest

from thesis_agents.mcp import cti_probe
from thesis_agents.mcp.client import MCPError, digest
from thesis_agents.mcp.cti_contracts import AssessmentRequest, SoftwareQuery
from thesis_agents.mcp.settings import MCPSettings


@pytest.fixture
def request_and_response():
    request = AssessmentRequest(
        software=SoftwareQuery(product="Synthetic missing product", version="1.0", evidence_id="E1")
    )
    matching = {
        "asset": {"product": request.software.product, "version": "1.0"},
        "query": {
            "product_terms": [request.software.product],
            "normalized_product_terms": ["synthetic missing product"],
            "vendor": None,
            "normalized_vendor": "",
        },
        "status": "no_match",
        "matches": [],
    }
    payload = {
        "contract": "cve2owl-assessment-v1",
        "backend_kind": "mock",
        "backend": "cve2owl-symbolic-v1",
        "request_sha256": digest(request.model_dump(mode="json")),
        "software": request.software.model_dump(mode="json"),
        "dataset": {"id": "synthetic-test", "sha256": "1" * 64, "kind": "fixture"},
        "engine_sha256": {"synthetic-test-engine": "2" * 64},
        "policy": {"match_limit": 5, "confidence_levels": ["high"], "vector_search": False},
        "matching": matching,
        "assessment": {
            "assessment_summary": {
                "confidence_required": ["high"],
                "assets_total": 1,
                "assets_with_assessments": 0,
                "matches_total": 0,
                "matches_evaluated": 0,
                "matches_skipped_by_confidence": 0,
                "vulnerability_status_counts": {},
            },
            "results": [],
        },
    }
    return request, payload


def test_no_match_preserves_unknown_coverage(request_and_response):
    request, payload = request_and_response
    result = cti_probe.validate_response(payload, request, "mock")
    assert result.matching.status == "no_match"
    assert result.assessment.assessment_summary.matches_evaluated == 0
    assert result.dataset.kind == "fixture"
    # Nessuna conversione in VulnerabilityReport, CVSS inventato o esito "sicuro".
    assert "cvss" not in result.model_dump_json()


@pytest.mark.parametrize(
    "path,value",
    [
        (("request_sha256",), "0" * 64),
        (("software", "evidence_id"), "another-request"),
        (("software", "version"), "2.0"),
        (("backend_kind",), "real"),
        (("dataset", "kind"), "real"),
        (("engine_sha256",), {}),
        (("matching", "asset", "product"), "another-product"),
        (("assessment", "assessment_summary", "matches_evaluated"), 1),
        (("assessment", "assessment_summary", "confidence_required"), ["medium"]),
        (("contract",), "another-contract"),
        (("policy", "vector_search"), True),
    ],
)
def test_inconsistent_response_rejected(request_and_response, path, value):
    request, payload = request_and_response
    target = payload
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    with pytest.raises(ValueError):
        cti_probe.validate_response(payload, request, "mock")


def test_real_is_explicit_and_does_not_accept_fixture(request_and_response):
    request, payload = request_and_response
    with pytest.raises(ValueError):
        cti_probe.validate_response(payload, request, "real")


def test_probe_writes_audit_and_refuses_overwrite(request_and_response, monkeypatch, tmp_path):
    request, payload = request_and_response

    class FakeConnection:
        def __init__(self, settings, *, contracts, audit):
            self.audit = audit

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def call_tool(self, name, arguments, parse):
            self.audit({"event": "synthetic-client-test"})
            return parse(payload)

    monkeypatch.setattr(cti_probe, "MCPClient", FakeConnection)
    settings = MCPSettings(url="http://127.0.0.1:8003/mcp", expected_kind="mock")
    output = tmp_path / "probe"
    cti_probe.run_probe(settings, request.software, output)
    summary = json.loads((output / "summary.json").read_text())
    assert summary["status"] == "validated"
    assert summary["llm_used"] is False
    assert json.loads((output / "assessment.json").read_text())["dataset"]["kind"] == "fixture"
    assert json.loads((output / "audit.json").read_text())
    with pytest.raises(FileExistsError):
        cti_probe.run_probe(settings, request.software, output)


def test_failed_probe_leaves_no_domain_result(request_and_response, monkeypatch, tmp_path):
    request, _ = request_and_response

    class FailedConnection:
        def __init__(self, settings, *, contracts, audit):
            audit({"event": "synthetic-connection-failure"})

        def __enter__(self):
            raise MCPError("Connection failed")

        def __exit__(self, *args):
            pass

    monkeypatch.setattr(cti_probe, "MCPClient", FailedConnection)
    settings = MCPSettings(url="http://127.0.0.1:8003/mcp", expected_kind="real")
    output = tmp_path / "failed"
    with pytest.raises(MCPError):
        cti_probe.run_probe(settings, request.software, output)
    assert not (output / "assessment.json").exists()
    assert json.loads((output / "summary.json").read_text())["status"] == "failed"
    assert json.loads((output / "audit.json").read_text())
