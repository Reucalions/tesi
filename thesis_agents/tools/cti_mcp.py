"""Adapter cve2owl: HTTP, mapping conservativo e snapshot, senza codice del backend.

Il nome osservato viene inviato immutato. Una sola identità candidata con
confidenza high può fondare finding; più identità non vengono risolte dall'LLM.
Il mapping non interpreta nuovamente gli intervalli né corregge le fonti.
"""

from pathlib import Path

from thesis_agents.mcp.client import MCPClient, digest
from thesis_agents.mcp.cti_client import cti_contracts, validate_response
from thesis_agents.mcp.cti_contracts import (
    TOOL,
    AssessmentRequest,
    AssessmentResponse,
    SoftwareQuery,
)
from thesis_agents.schemas import LookupResult, SoftwareObservation, VulnerabilityFinding
from thesis_agents.schemas.cti import CTICVEAssessment, CTIIdentity, CTILookupEvidence


def map_assessment(response: AssessmentResponse, observed: SoftwareObservation) -> LookupResult:
    """Normalizza dati validati, mantenendo sconosciuto ciò che non è valutabile."""
    if (response.software.product, response.software.version, response.software.evidence_id) != (
        observed.package,
        observed.version,
        observed.evidence_id,
    ):
        raise ValueError("La risposta CTI non riguarda l'osservazione runtime")
    validate_response(
        response.model_dump(mode="json"),
        AssessmentRequest(software=response.software),
        response.backend_kind,
    )
    matches = response.matching.matches
    resolved = len(matches) == 1 and matches[0].confidence == "high"
    identities = [
        CTIIdentity(
            **m.model_dump(include={"canonical_id", "product", "vendor", "confidence", "score"})
        )
        for m in matches
    ]
    assessments = []
    findings = {}
    for asset in response.assessment.results:
        for match in asset.matches:
            for entry in match.affected_entries:
                if entry.vulnerability_status is None or entry.vulnerability_reason is None:
                    raise ValueError("Valutazione CVE priva di esito o motivazione")
                positive = [
                    r.affected_version_id
                    for r in entry.version_rules
                    if r.evaluated
                    and r.matched_asset_version
                    and r.vulnerability_status == "vulnerable"
                ]
                if bool(positive) != (entry.vulnerability_status == "vulnerable"):
                    raise ValueError("Esito vulnerabile incoerente con le regole restituite")
                assessments.append(
                    CTICVEAssessment(
                        canonical_id=match.canonical_id,
                        cve_id=entry.cve_id,
                        affected_product_id=entry.affected_product_id,
                        affected_iri=entry.affected_iri,
                        json_path=entry.json_path,
                        status=entry.vulnerability_status,
                        rules=len(entry.version_rules),
                        evaluated_rules=sum(r.evaluated for r in entry.version_rules),
                        vulnerable_rule_ids=positive,
                        reason=entry.vulnerability_reason,
                    )
                )
                if resolved and positive:
                    findings[entry.cve_id] = VulnerabilityFinding(
                        cve_id=entry.cve_id,
                        package=observed.package,
                        observed_version=observed.version,
                        cvss=None,
                        cwe=[],
                        confidence=None,
                        evidence_ids=[observed.evidence_id],
                        source=f"{response.backend}; dataset={response.dataset.id}; "
                        f"sha256={response.dataset.sha256}",
                    )
    complete = (
        bool(assessments)
        and all(
            e.rules > 0
            and e.rules == e.evaluated_rules
            and e.status in ("vulnerable", "not_vulnerable")
            for e in assessments
        )
        and all(
            rule.vulnerability_status in ("vulnerable", "not_vulnerable")
            for asset in response.assessment.results
            for match in asset.matches
            for entry in match.affected_entries
            for rule in entry.version_rules
        )
    )
    coverage = (
        "complete"
        if complete
        else ("partial" if any(e.evaluated_rules for e in assessments) else "none")
    )
    if not matches:
        status = "no_match"
    elif not resolved:
        status = "ambiguous"
    elif findings:
        status = "matched"
    elif complete and all(e.status == "not_vulnerable" for e in assessments):
        status = "no_findings"
    else:
        status = "not_evaluable"
    return LookupResult(
        status=status,
        vulnerabilities=list(findings.values()),
        cti=CTILookupEvidence(
            backend_kind=response.backend_kind,
            backend=response.backend,
            observed_software=observed,
            identity_status="resolved" if resolved else ("ambiguous" if matches else "no_match"),
            identities=identities,
            assessments=assessments,
            rule_coverage=coverage,
            match_limit=response.policy.match_limit,
            dataset_id=response.dataset.id,
            dataset_sha256=response.dataset.sha256,
            engine_sha256=response.engine_sha256,
            request_sha256=response.request_sha256,
            response_sha256=digest(response.model_dump(mode="json")),
            missing_metadata=["cvss", "cwe", "numeric_confidence"],
            limitations=[
                "Coverage concerns returned candidates and rules, not the complete software risk.",
                "Matching is limited and heuristic; score is not a probability.",
                "No automatic alias mapping or version-rule repair is performed.",
                "An empty finding list does not establish software safety.",
            ],
        ),
    )


class CTIVulnerabilityTool:
    def __init__(self, client: MCPClient, output_dir: Path, *, expected_dataset_sha256=None):
        self.client = client
        self.output_dir = output_dir
        self.expected_dataset_sha256 = expected_dataset_sha256

    def lookup_vulnerabilities(self, software: SoftwareObservation) -> LookupResult:
        request = AssessmentRequest(
            software=SoftwareQuery(
                product=software.package, version=software.version, evidence_id=software.evidence_id
            )
        )

        def parse(payload):
            response = validate_response(payload, request, self.client.settings.expected_kind)
            if (
                self.expected_dataset_sha256 is not None
                and response.dataset.sha256 != self.expected_dataset_sha256
            ):
                raise ValueError("Dataset diverso dallo snapshot configurato")
            result = map_assessment(response, software)
            path = self.output_dir / "cti_assessment.json"
            data = response.model_dump_json(indent=2) + "\n"
            if path.exists():
                if path.read_text(encoding="utf-8") != data:
                    raise ValueError("Lo snapshot CTI è immutabile nel run")
            else:
                with path.open("x", encoding="utf-8") as stream:
                    stream.write(data)
            return result

        return self.client.call_tool(TOOL, request.model_dump(mode="json"), parse)


__all__ = ["CTIVulnerabilityTool", "cti_contracts", "map_assessment"]
