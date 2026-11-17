"""Extract the complete archived C1 trace for a semantic report, without service calls."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]
RUN = ROOT / "output/case-improvements-20261106/runs/C1-r2"
SOURCES = {}


def load(relative):
    path = RUN / relative
    SOURCES[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return json.loads(path.read_text())


def text_source(relative):
    path = RUN / relative
    SOURCES[str(path.relative_to(ROOT))] = hashlib.sha256(path.read_bytes()).hexdigest()
    return path.read_text()


def extract():
    runtime = load("sources/runtime_evidence.json")
    report = load("sources/vulnerability_report.json")
    assessment = load("sources/cti_assessment.json")
    context = load("sources/countermeasure_context.json")
    candidates = load("sources/candidate_strategies.json")
    preparation = load("preparation/canonical_preparation.json")
    owl = text_source("preparation/observed_assets.owl")
    aln = text_source("preparation/aln_ontology.owl")
    ranking = load("strategic/native_strategic_ranking.json")
    validation = load("validation/native_strategic_validation.json")
    recommendation = load("recommendation/native_strategic_recommendation.json")
    finalization = load("finalization/native_strategic_finalization.json")
    dag = load("dag.json")
    execution = load("execution.json")
    example = ranking["results"][0]
    attempt = validation["attempts"][0]
    final = finalization["results"][0]
    document = json.loads(final["record"]["document_json"])
    provenance = json.loads(final["record"]["provenance_json"])
    cve = example["cve_id"]
    entry = next(
        x
        for x in assessment["assessment"]["results"][0]["matches"][0]["affected_entries"]
        if x["cve_id"] == cve
    )
    observed = runtime["software"][0]
    assert observed["package"] == "logback-core" and observed["version"] == "1.5.24"
    assert len(runtime["telemetry"]["evidence_ids"]) == 5
    assert len(dag["nodes"]) == 8 and all(n["status"] == "completed" for n in dag["nodes"].values())
    assert all(
        x == dag["run_id"]
        for x in [
            preparation["run_id"],
            ranking["run_id"],
            validation["run_id"],
            recommendation["run_id"],
            finalization["run_id"],
            execution["run_id"],
        ]
    )
    assert hashlib.sha256(owl.encode()).hexdigest() == preparation["observed_assets_sha256"]
    assert hashlib.sha256(aln.encode()).hexdigest() == preparation["aln_ontology_sha256"]
    assert final["commit"]["successful"] and final["commit"]["validation_code"] == 0
    for field in ["document", "provenance"]:
        assert (
            "sha256:" + hashlib.sha256(final["record"][field + "_json"].encode()).hexdigest()
            == final["record"][field + "_sha256"]
        )
    readback_path = ROOT / "output/final-evaluation-20261113-r1/readbacks/verification.json"
    SOURCES[str(readback_path.relative_to(ROOT))] = hashlib.sha256(
        readback_path.read_bytes()
    ).hexdigest()
    readback = json.loads(readback_path.read_text())["C1"]
    assert readback["record_provenance_receipt_identical"]
    assert readback["transaction_id"] == final["commit"]["transaction_id"]
    out = dict(
        case="C1",
        run_id=dag["run_id"],
        dag_nodes=dag["nodes"],
        execution=execution,
        observed_software=observed,
        otel_observations=len(runtime["telemetry"]["evidence_ids"]),
        unobserved_flags={k: runtime[k] for k in ["endpoint_exposed", "deserialization_observed"]},
        identity=report["cti"]["identities"][0],
        vulnerability=report["vulnerabilities"][0],
        version_rules=entry["version_rules"],
        sbom_component=context["component"],
        osv_advisories=context["advisories"],
        candidates=candidates["strategies"],
        alias_namespace="https://swot.sisinflab.poliba.it/cve#",
        aliases={
            "a": attempt["request"]["asset_iri"],
            "p": "https://swot.sisinflab.poliba.it/cve#" + entry["affected_iri"],
            "v": "https://swot.sisinflab.poliba.it/cve#" + entry["version_rules"][0]["version_iri"],
            "c": "https://swot.sisinflab.poliba.it/cve#" + cve,
            "r": attempt["request"]["countermeasure_iri"],
        },
        observed_owl=owl,
        aln=aln,
        bindings=preparation["bindings"],
        graphs=preparation["graphs"],
        ranked=example["ranking"]["rankedStrategies"],
        native=attempt["response"]["reasoning"]["native"],
        semantic_status=attempt["response"]["status"],
        affinity=attempt["response"]["affinityScore"],
        bonus_evaluated=attempt["response"]["bonusEvaluated"],
        operational_context=attempt["request"]["operational_context"],
        operational_result=attempt["response"]["operational"],
        effective_status=attempt["response"]["effectiveStatus"],
        recommendation=recommendation["results"][0],
        source_digests=document["source_digests"],
        commit=final["commit"],
        readback=readback,
        provenance_counts={
            k: len(provenance[k]) for k in ["entities", "activities", "agents", "relations"]
        },
        provenance=provenance,
        sources_sha256=SOURCES,
        scope=(
            "Read-only extraction of one existing complete run; "
            "no new experiment or added ontology axioms."
        ),
    )
    (HERE / "esempio-semantico.json").write_text(
        json.dumps(out, ensure_ascii=False, indent=2) + "\n"
    )
    print(
        json.dumps(
            {
                "case": out["case"],
                "completed_nodes": len(dag["nodes"]),
                "source_files": len(SOURCES),
                "readback_equal": True,
            }
        )
    )


if __name__ == "__main__":
    extract()
