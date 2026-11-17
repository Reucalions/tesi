"""Consolidate frozen campaigns offline. Standard library only; never contacts backends.

Output directories must be fresh. Signed paired differences are retained, and
timings with different boundaries/cohorts are never pooled implicitly.
"""

from __future__ import annotations

import argparse
import json
import math
import statistics
from collections import Counter, defaultdict
from pathlib import Path

from collect_inventory import WORKSPACE, inventory, sha, write_csv, write_json

CAMPAIGN = Path("output/final-evaluation-20261113-r1")
BENCHMARK = Path("output/native-explanation-benchmark-20261113-r1")
COMPONENT = Path("output/component-metrics-20261112-r1/metrics.json")


def describe(values):
    values = list(values)
    if not values or any(isinstance(x, bool) or not math.isfinite(x) for x in values):
        raise ValueError("Expected a nonempty finite numeric series")
    return {
        "n": len(values),
        "min": min(values),
        "median": statistics.median(values),
        "max": max(values),
        "sample_sd": statistics.stdev(values) if len(values) > 1 else None,
    }


def check(condition, detail):
    if not condition:
        raise ValueError(detail)


def edges(native):
    return {
        (e["data"]["source"], e["data"]["target"]): e["data"]["label"]
        for e in native["graph"]["edges"]
    }


def consolidate(output, pipeline, ledger, inventory_snapshot=None):
    output.mkdir(parents=True, exist_ok=False)
    inputs = {}

    def read(path):
        path = WORKSPACE / path
        inputs[path.relative_to(WORKSPACE).as_posix()] = sha(path)
        return json.loads(path.read_text())

    def lines(path):
        path = WORKSPACE / path
        inputs[path.relative_to(WORKSPACE).as_posix()] = sha(path)
        return [json.loads(line) for line in path.read_text().splitlines() if line.strip()]

    series = []

    def observation(cohort, sample, metric, value, boundary, source):
        check(math.isfinite(value), f"Nonfinite {metric}")
        series.append(
            dict(
                cohort=cohort,
                sample=sample,
                metric=metric,
                seconds=value,
                boundary=boundary,
                source=str(source),
            )
        )

    component = read(COMPONENT)
    e = component["extraction"]["overall"]["entities"]
    for name, actual in {
        "precision": e["tp"] / (e["tp"] + e["fp"]),
        "recall": e["tp"] / (e["tp"] + e["fn"]),
        "f1": 2 * e["tp"] / (2 * e["tp"] + e["fp"] + e["fn"]),
    }.items():
        check(math.isclose(actual, e[name]), f"Invalid extraction {name}")
    for name in ["identity", "version_3class", "version_binary"]:
        row = component["cti"][name]
        check(math.isclose(row["accuracy"], row["correct"] / row["denominator"]), name)
    benchmark = read(BENCHMARK / "metrics.json")
    check(
        benchmark["completed"] == 30 and benchmark["independent_readback_equal"] == 30,
        "Incomplete benchmark",
    )

    weights = read(CAMPAIGN / "native/weight-results.json")
    protocol = read(CAMPAIGN / "native/protocol.json")
    check(len(weights) == 15, "Incomplete weight study")
    baseline = next(x["native"] for x in weights if x["variant"] == "baseline")
    base_edges = edges(baseline)
    base_scores = {x["name"]: x["score"] for x in baseline["suggestedStrategies"]}
    weight_summary = []
    for variant in protocol["weight_variants"]:
        rows = [x for x in weights if x["variant"] == variant["name"]]
        check(sorted(x["repetition"] for x in rows) == [1, 2, 3], "Missing weight repetition")
        for row in rows:
            current = row["native"]
            check(current["graph"]["nodes"] == baseline["graph"]["nodes"], "Changed nodes")
            actual = edges(current)
            check(actual.keys() == base_edges.keys(), "Changed topology")
            expected_edge = (variant["source"], variant["target"])
            changed = {k for k in base_edges if base_edges[k] != actual[k]}
            check(
                changed == (set() if variant["name"] == "baseline" else {expected_edge}),
                "Unexpected weight intervention",
            )
            for change in row["changes"]:
                k = (change["source"], change["target"])
                check(
                    change["before"] == base_edges[k] and change["after"] == actual[k],
                    "Getter/returned weight mismatch",
                )
                check(
                    math.isclose(
                        change["after"], change["before"] * variant["factor"], rel_tol=2e-7
                    ),
                    "Incorrect factor",
                )
            check(current == rows[0]["native"], "Weight repetition output differs")
            check(
                all(math.isfinite(x["score"]) for x in current["suggestedStrategies"]),
                "Nonfinite scores",
            )
            observation(
                "weight-" + row["variant"],
                str(row["repetition"]),
                "compute_rank",
                row["compute_seconds"],
                "Native ComputeRank including logging; excludes ontology/graph load",
                CAMPAIGN / "native/weight-results.json",
            )
        scores = {x["name"]: x["score"] for x in rows[0]["native"]["suggestedStrategies"]}
        check(scores.keys() == base_scores.keys(), "Changed candidate set")
        weight_summary.append(
            dict(
                variant=variant["name"],
                repetitions=3,
                changes=rows[0]["changes"],
                max_absolute_score_delta=max(abs(scores[k] - base_scores[k]) for k in scores),
                winner=max(scores, key=scores.get),
                repeat_outputs_identical=True,
            )
        )

    offchain = read(CAMPAIGN / "native/offchain-results.json")
    plan = read(CAMPAIGN / "native/offchain-plan.json")
    check(
        len(offchain) == len(plan) == 30 and {x["id"] for x in offchain} == {x["id"] for x in plan},
        "Incomplete offchain cohort",
    )
    comparisons = []
    for row in offchain:
        check(row["raw_native_and_adapted_outputs_equal"] is True, "Offchain output mismatch")
        source = BENCHMARK / "trials" / row["id"] / "collection-timings.json"
        on = {x["tool"]: x for x in read(source)}
        case = row["id"].split("-original")[0].split("-reordered")[0]
        pair = {
            "cohort": "offchain-vs-mcp",
            "sample": row["id"],
            "case": case,
            "exact_native_and_adapted_equal": True,
        }
        for local, remote in [("rank_seconds", "rank_graph"), ("store_seconds", "store_graph")]:
            check(on[remote]["success"] is True, "Failed onchain timing")
            pair[remote + "_onchain_seconds"] = on[remote]["elapsed_seconds"]
            pair[remote + "_offchain_seconds"] = row[local]
            pair[remote + "_difference_seconds"] = on[remote]["elapsed_seconds"] - row[local]
            observation(
                "offchain-" + case,
                row["id"],
                remote,
                row[local],
                "Same Go/native contract; in-memory state; excludes client/Fabric",
                CAMPAIGN / "native/offchain-results.json",
            )
            observation(
                "onchain-" + case,
                row["id"],
                remote,
                on[remote]["elapsed_seconds"],
                "MCP call including client, transport, Fabric and contract",
                source,
            )
        comparisons.append(pair)
    pairs = read(CAMPAIGN / "commit-pairs/results.json")
    check(len(pairs) == 15, "Incomplete REST pairs")
    for row in pairs:
        check(
            row["evaluate_state_not_committed"] and row["invoke_outputs_match"],
            "REST state mismatch",
        )
        check(
            math.isclose(
                row["invoke_minus_evaluate_seconds"],
                row["seconds"]["invoke"] - row["seconds"]["query"],
            ),
            "Invalid signed commit difference",
        )
        comparisons.append(
            dict(
                cohort="rest-invoke-minus-evaluate",
                sample=row["id"],
                case=f"baseline-{row['case']}",
                difference_seconds=row["invoke_minus_evaluate_seconds"],
            )
        )
        for method, seconds in row["seconds"].items():
            observation(
                f"rest-baseline-{row['case']}",
                row["id"],
                method,
                seconds,
                "Same REST client and RankGraph; evaluate vs endorse/submit/commit",
                CAMPAIGN / "commit-pairs/results.json",
            )

    semantic = read(CAMPAIGN / "semantic/results.json")
    check(len(semantic) == 6, "Incomplete semantic study")
    semantic_summary = []
    for row in semantic:
        response = row["response"]["response"]
        check(response["isCoherent"] is True, "Incoherent semantic fixture")
        if row["case"] == "logback-abduction-bonus":
            check(
                "Penalty: 38.00" in response["abductionResult"]
                and "Incentive: 1.00" in response["bonusResult"]
                and response["contractionResult"] == "",
                "Unexpected abduction/bonus",
            )
        else:
            check(
                "Penalty: 2.00" in response["contractionResult"]
                and "Give up:" in response["contractionResult"]
                and not response["abductionResult"]
                and not response["bonusResult"],
                "Unexpected contraction",
            )
        semantic_summary.append(
            {
                "case": row["case"],
                "repetition": row["repetition"],
                **{k: response[k] for k in ["abductionResult", "bonusResult", "contractionResult"]},
            }
        )
        observation(
            row["case"],
            str(row["repetition"]),
            "AnalyzeOntology",
            row["event"]["elapsed_seconds"],
            "REST evaluate of transient existing ontology; includes transport/reasoner",
            CAMPAIGN / "semantic/results.json",
        )
    controls = read(CAMPAIGN / "semantic-controls/results.json")
    check(
        [x["semantic_status"] for x in controls[0]["semantic_attempts"]] == ["accepted"],
        "Top semantic control",
    )
    check(
        [x["semantic_status"] for x in controls[1]["semantic_attempts"]]
        == ["rejected", "requires_prerequisites", "requires_prerequisites", "accepted"],
        "Semantic traversal control",
    )
    check(
        all(x["application_acceptance_claimed"] is False for x in controls),
        "Invalid application claim",
    )

    ablation = read(CAMPAIGN / "ablation-r2/results.json")
    ap = read(CAMPAIGN / "ablation-r2/protocol.json")
    check(len(ablation) == 2, "Incomplete runtime comparison")
    preparations = [
        read(CAMPAIGN / "ablation-r2" / arm / "preparation/canonical_preparation.json")
        for arm in ["with-runtime", "without-runtime"]
    ]
    for key in ["graphs", "bindings", "observed_assets_sha256", "aln_ontology_sha256"]:
        check(preparations[0][key] == preparations[1][key], f"Different runtime comparison {key}")
    for filename in [
        "observed_assets.owl",
        "aln_ontology.owl",
        "ranking-requests/CVE-2026-1225.json",
    ]:
        paths = [
            WORKSPACE / CAMPAIGN / "ablation-r2" / arm / "preparation" / filename
            for arm in ["with-runtime", "without-runtime"]
        ]
        check(paths[0].read_bytes() == paths[1].read_bytes(), f"Different generated {filename}")
        for p in paths:
            inputs[p.relative_to(WORKSPACE).as_posix()] = sha(p)
    check(
        ap["arms"]["with-runtime"]["runtime_digest"]
        != ap["arms"]["without-runtime"]["runtime_digest"],
        "No runtime intervention",
    )
    before_after = []
    for row in ablation:
        arm = row["arm"]
        result = row["recommendation"]["results"][0]
        response = row["validation"]["attempts"][0]["response"]
        check(
            result["outcome"] == "requires_prerequisites"
            and result["selected_strategy_id"] is None,
            "Unexpected runtime comparison decision",
        )
        check(row["finalization"]["shared_finalization"] == "completed", "Incomplete finalization")
        check(
            response["reasoning"]["native"]["abductionPenalty"] == 38
            and response["bonusEvaluated"] is False,
            "Unexpected application reasoning",
        )
        before_after.append(
            dict(
                arm=arm,
                ranking_proposal="S_UPGRADE",
                ranking_score=1.0,
                score_method="single_candidate_convention_v1",
                semantic=response["status"],
                operational=response["operational"]["status"],
                final_outcome=result["outcome"],
                selected=None,
                block=row["finalization"]["results"][0]["commit"]["block_number"],
            )
        )
        source = CAMPAIGN / "ablation-r2" / arm
        observation(
            "artifact-replay-" + arm,
            row["run_id"],
            "downstream_elapsed",
            row["elapsed_seconds"],
            "Generator through finalization; no upstream LLM workers",
            source / "summary.json",
        )
        for event in lines(source / "generator-functions.jsonl"):
            check(event["success"] is True, "Failed generator function")
            observation(
                "generator-" + arm,
                row["run_id"],
                event["phase"],
                event["elapsed_seconds"],
                "Existing function plus thin timer wrapper; graph phase includes KG lookup",
                source / "generator-functions.jsonl",
            )
        for event in lines(source / "shared-mcp-events.jsonl"):
            if event.get("elapsed_seconds") is not None:
                check(event["status"] == "validated", "Unvalidated MCP event")
                observation(
                    "artifact-replay-" + arm,
                    row["run_id"],
                    event["tool"],
                    event["elapsed_seconds"],
                    "Aggregate domain MCP call; finalization includes decision and PROV-O",
                    source / "shared-mcp-events.jsonl",
                )

    runtime_inventory = read(CAMPAIGN / "runtime-inventory/results.json")
    check(len(runtime_inventory) == 15, "Incomplete CTI inventory comparison")
    inventory_summary = {
        arm: dict(Counter(x["lookup_status"] for x in runtime_inventory if x["arm"] == arm))
        for arm in ["with-runtime", "without-runtime"]
    }
    workers = read(CAMPAIGN / "telemetry-worker/results.json")
    check(
        len(workers) == 3 and all(x["success"] for x in workers), "Incomplete isolated worker study"
    )
    for row in workers:
        source = CAMPAIGN / "telemetry-worker" / f"r{row['repetition']}"
        observation(
            "isolated-telemetry-worker",
            str(row["repetition"]),
            "worker_step",
            row["elapsed_seconds"],
            "Production worker step, real model/tools/publication; managers excluded; "
            "first load retained",
            source / "measurement.json",
        )
        for event in lines(source / "telemetry-events.jsonl"):
            check(event["status"] == "validated", "Failed telemetry gateway event")
            observation(
                "isolated-telemetry-worker",
                str(row["repetition"]),
                "collect_telemetry",
                event["elapsed_seconds"],
                "HTTP replay gateway only; original SDK acquisition excluded",
                source / "telemetry-events.jsonl",
            )
    cases = []
    for case in ["C1-r2", "C2-r1", "C3-r1", "C4-r3"]:
        source = Path("output/case-improvements-20261106/cases") / case / "summary.json"
        row = read(source)
        check(
            row["exit_code"] == 0 and row["remediation_executed"] is False,
            "Unexpected primary case",
        )
        execution = row["execution"]
        cases.append(
            dict(
                case=case,
                seconds=row["elapsed_seconds"],
                status=execution["status"],
                outcomes=execution.get("outcomes_by_cve", {"assessment": execution.get("outcome")}),
                finalization=execution["shared_finalization"],
                action_execution=execution["action_execution"],
                source=str(source),
            )
        )
        observation(
            "full-launcher-" + case,
            case,
            "end_to_end",
            row["elapsed_seconds"],
            "Real CAMEL runner including teardown; archived SDK replay",
            source,
        )
        run = WORKSPACE / "output/case-improvements-20261106/runs" / case
        for relative in [
            "sources/mcp_events.jsonl",
            "sources/telemetry_events.jsonl",
            "sources/supply_chain_events.jsonl",
            "preparation/preparation_events.jsonl",
            "strategic/strategic_events.jsonl",
            "validation/validation_events.jsonl",
            "shared_mcp_events.jsonl",
        ]:
            p = run / relative
            if p.exists():
                for idx, event in enumerate(lines(p)):
                    if event.get("elapsed_seconds") is not None:
                        observation(
                            "full-launcher-" + case,
                            f"{case}:{relative}:{idx + 1}",
                            event.get("tool", event.get("event", "unknown")),
                            event["elapsed_seconds"],
                            "Recorded domain/gateway call; overlapping events must not be summed",
                            p.relative_to(WORKSPACE),
                        )

    readbacks = read(CAMPAIGN / "readbacks/verification.json")
    check(
        len(readbacks) == 5
        and all(x["record_provenance_receipt_identical"] for x in readbacks.values()),
        "Readback mismatch",
    )
    catalog = read(Path("config/metrics-evidence.v2.json"))
    check(
        len(catalog["metrics"]) == 32 and len({x["id"] for x in catalog["metrics"]}) == 32,
        "Coverage catalog",
    )
    roots = {"framework": WORKSPACE, "pipeline": pipeline, "ledger": ledger}
    if inventory_snapshot is None:
        records, unmatched = inventory(catalog, roots)
    else:
        records = json.loads(inventory_snapshot.read_text())
        unmatched = []
        check(len({r["id"] for r in records}) == len(records), "Duplicate snapshot paths")
    stats_groups = defaultdict(list)
    for row in series:
        stats_groups[(row["cohort"], row["metric"], row["boundary"])].append(row["seconds"])
    stats = [
        dict(cohort=k[0], metric=k[1], boundary=k[2], **describe(v))
        for k, v in sorted(stats_groups.items())
    ]
    paired_stats = []
    for case in [f"baseline-{i}" for i in range(1, 6)]:
        for metric in ["rank_graph", "store_graph"]:
            values = [
                r[metric + "_difference_seconds"]
                for r in comparisons
                if r["cohort"] == "offchain-vs-mcp" and r["case"] == case
            ]
            paired_stats.append(
                dict(cohort="offchain-vs-mcp", case=case, metric=metric, **describe(values))
            )
        values = [
            r["difference_seconds"]
            for r in comparisons
            if r["cohort"] == "rest-invoke-minus-evaluate" and r["case"] == case
        ]
        paired_stats.append(
            dict(
                cohort="rest-invoke-minus-evaluate",
                case=case,
                metric="RankGraph",
                **describe(values),
            )
        )
    result = dict(
        contract="final-evaluation-results-v1",
        date="2026-11-13",
        component_metrics=component,
        corrected_native_benchmark=benchmark,
        weight_sensitivity=weight_summary,
        native_semantic_diagnostics=semantic_summary,
        baseline_semantic_controls=controls,
        runtime_comparison=dict(
            protocol=ap,
            generated_graph_owl_aln_equal=True,
            before_after_validation=before_after,
            inventory_lookup_statuses=inventory_summary,
        ),
        cases=cases,
        fresh_readbacks=readbacks,
        statistics=stats,
        paired_statistics=paired_stats,
        evidence_inventory_files=len(records),
        unmatched_patterns=unmatched,
        limitations=[
            "Assisted reference, no independent human review",
            "No real application accepted candidate/fallback",
            "No node-prior weight API",
            "Baseline reflexivity controls are not mitigation applicability",
            "No complete CAMEL runtime ablation; fixed artifact replay only",
            "No pure consensus isolation",
            "No real-time event-to-decision latency or actuation",
            "Small samples; no population/significance claim",
        ],
    )
    write_json(output / "results.json", result)
    write_json(output / "inventory.json", records)
    write_json(output / "coverage.json", catalog["metrics"])
    write_json(output / "input-manifest.json", inputs)
    write_csv(
        output / "series.csv",
        series,
        ["cohort", "sample", "metric", "seconds", "boundary", "source"],
    )
    write_csv(
        output / "statistics.csv",
        stats,
        ["cohort", "metric", "boundary", "n", "min", "median", "max", "sample_sd"],
    )
    write_csv(
        output / "paired-statistics.csv",
        paired_stats,
        ["cohort", "case", "metric", "n", "min", "median", "max", "sample_sd"],
    )
    write_csv(output / "comparisons.csv", comparisons, sorted({k for r in comparisons for k in r}))
    write_csv(
        output / "case-outcomes.csv",
        cases,
        ["case", "seconds", "status", "outcomes", "finalization", "action_execution", "source"],
    )
    write_csv(
        output / "coverage.csv",
        catalog["metrics"],
        ["id", "section", "name", "status", "evidence", "available", "gap", "next"],
    )
    write_csv(
        output / "inventory.csv", records, ["repository", "path", "size_bytes", "sha256", "groups"]
    )
    write_json(
        output / "manifest.json", {p.name: sha(p) for p in sorted(output.iterdir()) if p.is_file()}
    )
    print(
        json.dumps(
            {
                "output": str(output),
                "input_files": len(inputs),
                "inventory_files": len(records),
                "observations": len(series),
                "paired_comparisons": len(comparisons),
                "unmatched_patterns": len(unmatched),
            }
        )
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--evidence-root",
        type=Path,
        default=WORKSPACE,
        help="Root of archived inputs; defaults to this repository",
    )
    parser.add_argument(
        "--inventory-snapshot",
        type=Path,
        help="Reuse a frozen inventory without reading external repositories",
    )
    parser.add_argument(
        "--pipeline",
        type=Path,
        default=Path("/Users/reucalion/Desktop/agent-based-cti-argumentation-pipeline"),
    )
    parser.add_argument(
        "--ledger",
        type=Path,
        default=Path("/Users/reucalion/Desktop/semantic-cti-ledger-argumentation"),
    )
    args = parser.parse_args()
    WORKSPACE = args.evidence_root.resolve()
    consolidate(args.output, args.pipeline, args.ledger, args.inventory_snapshot)
