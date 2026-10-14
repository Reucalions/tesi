"""Mapping conservativo di risposte catturate; nessun backend o LLM live."""

import json
from pathlib import Path

import pytest

from thesis_agents.backends import BackendSettings
from thesis_agents.mcp.client import digest, schema_shape
from thesis_agents.mcp.cti_contracts import AssessmentResponse
from thesis_agents.schemas import LookupResult, SoftwareObservation
from thesis_agents.tools.cti_mcp import map_assessment
from thesis_agents.tools.strategic_mcp import strategic_contracts
from thesis_agents.tools.vulnerability_mcp import lookup_contracts

DATA = Path(__file__).parent / "data/cti"


def captured(name):
    response = AssessmentResponse.model_validate_json((DATA / f"{name}.json").read_text())
    query = response.software
    observed = SoftwareObservation(
        package=query.product, version=query.version, evidence_id=query.evidence_id
    )
    return response, observed


@pytest.mark.parametrize(
    "name,status,identity,coverage",
    [
        ("runtime-package", "ambiguous", "ambiguous", "none"),
        ("canonical-log4j2", "not_evaluable", "resolved", "none"),
        ("affected-range", "ambiguous", "ambiguous", "partial"),
        ("outside-range", "ambiguous", "ambiguous", "partial"),
        ("unknown-version", "not_evaluable", "resolved", "none"),
        ("absent-product", "no_match", "no_match", "none"),
        ("core-negative", "no_findings", "resolved", "complete"),
    ],
)
def test_inconclusive_or_negative_results_never_become_findings(name, status, identity, coverage):
    response, observed = captured(name)
    result = map_assessment(response, observed)
    assert (result.status, result.cti.identity_status, result.cti.rule_coverage) == (
        status,
        identity,
        coverage,
    )
    assert result.vulnerabilities == []
    assert result.cti.observed_software == observed
    assert result.cti.response_sha256 == digest(response.model_dump(mode="json"))


def test_positive_findings_preserve_observation_and_do_not_invent_metadata():
    response, observed = captured("canonical-log4j-core")
    result = map_assessment(response, observed)
    assert result.status == "matched"
    assert {f.cve_id for f in result.vulnerabilities} == {
        "CVE-2025-68161",
        "CVE-2026-34477",
        "CVE-2026-34480",
    }
    for finding in result.vulnerabilities:
        assert (finding.package, finding.observed_version) == (observed.package, observed.version)
        assert finding.evidence_ids == [observed.evidence_id]
        assert finding.cvss is None and finding.confidence is None and finding.cwe == []
    assert result.cti.missing_metadata == ["cvss", "cwe", "numeric_confidence"]
    assert len(result.cti.assessments) == 4  # Include anche la CVE non vulnerabile.


@pytest.mark.parametrize(
    "name,status", [("core-negative", "not_evaluable"), ("canonical-log4j-core", "matched")]
)
def test_partial_rules_do_not_support_a_complete_negative_assessment(name, status):
    response, observed = captured(name)
    rule = response.assessment.results[0].matches[0].affected_entries[-1].version_rules[-1]
    rule.evaluated = False
    rule.vulnerability_status = "not_evaluable"
    rule.reason = "Synthetic unevaluable rule for coverage regression"
    result = map_assessment(response, observed)
    assert result.status == status
    assert result.cti.rule_coverage == "partial"


@pytest.mark.parametrize("fault", ["observation", "identity", "cve", "positive-rule"])
def test_inconsistent_source_references_or_positive_claims_are_rejected(fault):
    response, observed = captured("canonical-log4j-core")
    assessed = response.assessment.results[0].matches[0]
    if fault == "observation":
        observed.version = "0.0.0"
    elif fault == "identity":
        assessed.product = "Another product"
    elif fault == "cve":
        assessed.affected_entries[0].cve_id = "CVE-2000-0001"
    else:
        assessed.affected_entries[0].version_rules[0].matched_asset_version = False
    with pytest.raises(ValueError):
        map_assessment(response, observed)


def test_extended_states_require_cti_and_legacy_metadata_stays_required():
    with pytest.raises(ValueError, match="require CTI"):
        LookupResult(status="no_findings", vulnerabilities=[])
    result = map_assessment(*captured("canonical-log4j-core"))
    with pytest.raises(ValueError, match="numeric metadata"):
        LookupResult(status="matched", vulnerabilities=result.vulnerabilities)


def test_legacy_mcp_wire_schemas_are_unchanged():
    expected = json.loads((DATA.parent / "mcp-v1-schema-hashes.json").read_text())
    contracts = lookup_contracts()
    for service in ("ranking", "semantic", "provenance"):
        contracts.update(strategic_contracts(service))
    assert {
        name: [digest(schema_shape(s)) for s in schemas] for name, schemas in contracts.items()
    } == expected


def test_cti_profile_rejects_legacy_semantic_wire_instead_of_losing_metadata():
    remote = {"transport": "mcp", "url": "http://127.0.0.1:8003/mcp", "expected_kind": "real"}
    with pytest.raises(ValueError, match="semantic-validation-v1"):
        BackendSettings(vulnerability_adapter="cve2owl-v1", vulnerability=remote, semantic=remote)
    with pytest.raises(ValueError, match="endpoint MCP"):
        BackendSettings(vulnerability_adapter="cve2owl-v1")
