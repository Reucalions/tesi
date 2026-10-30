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
from thesis_agents.schemas.telemetry_source import TelemetryInput


def build_explanation(
    case: StaticTelemetry | TelemetryInput,
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
    if evidence.telemetry is not None:
        ref = evidence.telemetry
        add(
            "limitation",
            f"OpenTelemetry source {quoted(ref.source_id)}; acquisition={ref.acquisition}; "
            f"observed window {ref.query.start_time.isoformat()} "
            f"to {ref.query.end_time.isoformat()}. "
            "Null flags mean unknown. "
            + (
                "Source identity comes from a recorded dataset binding, not runtime "
                "instance instrumentation. "
                if ref.recorded_context
                else "Instrumentation-declared identity is not a complete inventory. "
            )
            + "Reading a recorded export now does not make its observations current.",
            source("runtime_evidence", "/telemetry"),
        )
        if ref.recorded_context:
            context = ref.recorded_context
            add(
                "limitation",
                f"Recorded testbed host {quoted(context.host)}, service {quoted(context.service)}; "
                f"scope {quoted(context.scope_id)} is not an observed runtime instance ID. "
                f"Inventory snapshot reports {quoted(context.package_name)} "
                f"{quoted(context.package_version)} on {context.distribution} "
                f"{context.distribution_version}, collected at "
                f"{context.facts_collected_at.isoformat()}. It does not attest the package "
                "at every earlier event; telemetry alone does not establish "
                "distribution patch status. "
                "Runtime upstream version and inventory package revision remain separate.",
                source("runtime_evidence", "/telemetry/recorded_context"),
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
    elif report.lookup_status in ("ambiguous", "no_match", "not_evaluable", "no_findings"):
        meanings = {
            "ambiguous": "product identity remains unresolved; no candidate was silently selected",
            "no_match": "the backend returned no matching product; coverage remains unknown",
            "not_evaluable": (
                "the returned version rules do not support a complete negative assessment"
            ),
            "no_findings": "no confirmed findings within the returned identity and evaluated rules",
        }
        if report.package_assessment is not None:
            meanings["not_evaluable"] = (
                "the inventory assessment does not establish historical runtime applicability"
            )
        add(
            "limitation",
            f"{producers['vulnerability_report']} reports lookup_status={report.lookup_status}: "
            f"{meanings[report.lookup_status]}. An empty finding list is not proof of safety.",
            source("vulnerability_report", "/lookup_status"),
            source(
                "vulnerability_report",
                "/package_assessment" if report.package_assessment else "/cti",
            ),
        )
    else:
        for i, finding in enumerate(report.vulnerabilities):
            add(
                "reported_fact",
                f"{producers['vulnerability_report']} reports {quoted(finding.cve_id)} with "
                + (f"CVSS {finding.cvss:g}" if finding.cvss is not None else "CVSS unavailable")
                + f", source {quoted(finding.source)}. "
                "These are lookup results, not independent verification "
                "or a remediation-version recommendation.",
                *(
                    source("vulnerability_report", f"/vulnerabilities/{i}/{p}")
                    for p in ("cve_id", "cvss", "source")
                ),
            )
    if report.package_assessment is not None:
        package = report.package_assessment
        add(
            "reported_fact",
            f"Ubuntu inventory assessment ({package.backend_kind}), "
            f"identity={package.identity_status}, "
            f"package {package.inventory_package} {package.inventory_version}: "
            + ", ".join(f"{key}={value}" for key, value in package.counts.items())
            + ". These retrospective package verdicts do not establish historical runtime "
            "applicability or exploitation conditions. Full evidence remains in "
            f"{package.response_file}, SHA-256 {package.response_sha256}.",
            source("vulnerability_report", "/package_assessment"),
        )
    if report.cti is not None:
        add(
            "limitation",
            f"CTI backend {quoted(report.cti.backend)} ({report.cti.backend_kind}), "
            f"dataset {quoted(report.cti.dataset_id)}, SHA-256 {report.cti.dataset_sha256}. "
            f"Identity status={report.cti.identity_status}; "
            f"rule coverage={report.cti.rule_coverage} "
            "within returned candidates only. Matching scores are not probabilities. "
            f"Unavailable metadata: {quoted(report.cti.missing_metadata)}. "
            "Dataset completeness and independent vulnerability verification are not established.",
            source("vulnerability_report", "/cti"),
        )
    add(
        "reported_fact",
        f"{producers['candidate_strategies']} published {len(candidates.strategies)} candidates. "
        "This generated set is not an exhaustive inventory of possible countermeasures.",
        source("candidate_strategies", "/strategies"),
    )
    if candidates.verification_requests:
        add(
            "limitation",
            f"CountermeasureAgent published {len(candidates.verification_requests)} pending "
            "evidence requests: "
            + ", ".join(
                f"{r.kind} ({len(r.cve_ids)} CVEs)" for r in candidates.verification_requests
            )
            + ". These checks have not been executed and provide no new runtime evidence. "
            "They are excluded from remediation ranking and selection.",
            source("candidate_strategies", "/verification_requests"),
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
    if ranking.backend == "empty-strategy-gate-v1":
        add(
            "limitation",
            "The empty-strategy gate returned an empty ranking. No BWAF ranking or semantic "
            "validation was executed; pending evidence requests are not selectable strategies.",
            source("ranking", "/backend"),
            source("ranking", "/ranking"),
            source("semantic_validation", "/validations"),
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
    elif report.lookup_status in ("ambiguous", "no_match", "not_evaluable"):
        conclusion = (
            f"Decision: insufficient_evidence (lookup_status={report.lookup_status}). "
            "No strategy selected; no candidates were validated. This does not establish "
            "that every countermeasure is invalid."
        )
    elif report.lookup_status == "no_findings":
        conclusion = (
            "Decision: no_findings within returned identity and evaluated rules. "
            "No strategy selected or validated; this is not a claim of software safety."
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
