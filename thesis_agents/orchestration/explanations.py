"""Spiegazione controllata della decisione a partire dai soli campi strutturati.

Non valuta il linguaggio naturale: non riusa descrizioni, rationale, observations
o spiegazioni dei tool come fatti. Ogni affermazione ha fonti risolvibili nei JSON.
La scelta resta quella proposta dallo Strategic e verificata da ArtifactSession.
"""

import json

from thesis_agents.schemas import (
    CandidateStrategies,
    RankingResult,
    RuntimeEvidence,
    SemanticValidationReport,
    StaticTelemetry,
    VulnerabilityReport,
)
from thesis_agents.schemas.decision import ExplanationClaim, ExplanationSource


def build_explanation(
    case: StaticTelemetry,
    evidence: RuntimeEvidence,
    report: VulnerabilityReport,
    candidates: CandidateStrategies,
    ranking: RankingResult,
    validations: SemanticValidationReport,
    selected: str | None,
    producers: dict[str, str],
) -> list[ExplanationClaim]:
    # Quota i valori dell'input per presentarli come dati, non come istruzioni.
    def quoted(value):
        return json.dumps(value, ensure_ascii=False)

    def source(artifact, pointer):
        return ExplanationSource(artifact=artifact, pointer=pointer, producer=producers[artifact])

    claims = []

    def add(category, text, *sources):
        claims.append(ExplanationClaim(category=category, text=text, sources=list(sources)))

    software = [{"package": s.package, "version": s.version} for s in evidence.software]
    add(
        "reported_fact",
        f"{producers['runtime_evidence']} reports service {quoted(evidence.service_name)}, "
        f"software {quoted(software)}, endpoint_exposed={quoted(evidence.endpoint_exposed)}, "
        f"deserialization_observed={quoted(evidence.deserialization_observed)}. "
        "These observations do not establish a confirmed exploit.",
        *(
            source("runtime_evidence", p)
            for p in (
                "/service_name",
                "/software",
                "/endpoint_exposed",
                "/deserialization_observed",
            )
        ),
    )
    if report.lookup_status == "unsupported":
        add(
            "limitation",
            f"{producers['vulnerability_report']} reports lookup_status=unsupported: the "
            "configured lookup does not cover this software/version. Vulnerability status "
            "and vendor support status remain unknown; "
            "an empty findings list is not proof of safety.",
            source("vulnerability_report", "/lookup_status"),
            source("vulnerability_report", "/vulnerabilities"),
        )
    else:
        for i, finding in enumerate(report.vulnerabilities):
            add(
                "reported_fact",
                f"{producers['vulnerability_report']} reports {quoted(finding.cve_id)} with "
                f"CVSS {finding.cvss:g}, source {quoted(finding.source)}. "
                "These are lookup results, not independent verification "
                "or a remediation-version recommendation.",
                *(
                    source("vulnerability_report", f"/vulnerabilities/{i}/{p}")
                    for p in ("cve_id", "cvss", "source")
                ),
            )
    add(
        "reported_fact",
        f"{producers['candidate_strategies']} published {len(candidates.strategies)} candidates. "
        "This generated set is not an exhaustive inventory of possible countermeasures.",
        source("candidate_strategies", "/strategies"),
    )
    for i, candidate in enumerate(candidates.strategies):
        add(
            "estimate",
            f"Candidate {quoted(candidate.id)} ({candidate.action}): security_benefit="
            f"{candidate.security_benefit:g}, operational_impact={candidate.operational_impact:g}. "
            f"These are estimates supplied by {producers['candidate_strategies']}, "
            "not measurements.",
            *(
                source("candidate_strategies", f"/strategies/{i}/{p}")
                for p in ("id", "action", "security_benefit", "operational_impact")
            ),
        )
    add(
        "reported_fact",
        f"Ranking backend {quoted(ranking.backend)} returned "
        f"{quoted([r.model_dump(mode='json') for r in ranking.ranking])}. "
        "These scores do not establish measured effectiveness or operational safety.",
        source("ranking", "/backend"),
        source("ranking", "/ranking"),
    )
    add(
        "reported_fact",
        f"Input capabilities: {quoted(case.available_capabilities)}; "
        f"prohibited actions: {quoted(case.prohibited_actions)}.",
        source("input", "/available_capabilities"),
        source("input", "/prohibited_actions"),
    )
    for i, validation in enumerate(validations.validations):
        add(
            "reported_fact",
            f"Validation backend {quoted(validation.backend)} returned {validation.status} "
            f"for {quoted(validation.strategy_id)}: missing_requirements="
            f"{quoted(validation.missing_requirements)}, conflicts={quoted(validation.conflicts)}.",
            *(
                source("semantic_validation", f"/validations/{i}/{p}")
                for p in ("backend", "status", "strategy_id", "missing_requirements", "conflicts")
            ),
        )
    if report.lookup_status == "unsupported":
        conclusion = (
            "Decision: insufficient_evidence. No strategy selected because the lookup "
            "lacks coverage. No candidates were validated; this does not establish "
            "that every countermeasure is invalid."
        )
    elif selected is None:
        conclusion = (
            "Decision: no_valid_strategy. All published candidates were rejected under "
            "the supplied capabilities and policies. This does not prove that no other "
            "real-world solution exists."
        )
    else:
        conclusion = (
            f"Decision: selected {quoted(selected)}, the first accepted candidate in "
            "backend ranking order. Acceptance means the configured validator's checks "
            "passed, not proof of safety."
        )
    add(
        "decision",
        conclusion + " This prototype proposes actions; it executes no remediation.",
        source("vulnerability_report", "/lookup_status"),
        source("candidate_strategies", "/strategies"),
        source("ranking", "/ranking"),
        source("semantic_validation", "/validations"),
    )
    return claims
