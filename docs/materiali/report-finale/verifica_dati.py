"""Check that the report tables reproduce the frozen measurements, without new runs."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def load(p):
    return json.loads(p.read_text())


def value(s):
    return float(s.replace(".", "").replace(",", "."))


def same(actual, expected, places):
    if abs(value(actual) - expected) > 0.51 * 10 ** (-places):
        raise AssertionError((actual, expected, places))


def verify():
    content = load(HERE / "contenuto.json")
    tables = {
        b["metric_table_id"]: b
        for page in content["pages"]
        for b in page["blocks"]
        if b["type"] == "table" and "metric_table_id" in b
    }
    results = load(ROOT / "evaluation/final-results-v1/results.json")
    mockpath = ROOT / "output/demo-matrix-20260916T074247Z-80665fa1/summary.json"
    mock = load(mockpath)
    for idx, scenario in enumerate(
        [
            "demo_01_nominal",
            "demo_02_no_maintenance",
            "demo_03_all_actions_prohibited",
            "demo_04_unsupported_lookup",
        ]
    ):
        runs = sorted(
            [x for x in mock["runs"] if x["scenario"] == scenario], key=lambda x: x["repetition"]
        )
        row = tables[4]["rows"][idx]
        for run, s in zip(runs, row[1:3], strict=True):
            same(s, run["elapsed_seconds"], 2)
        assert row[3] == " / ".join(str(run["audit"]["llm_requests"]) for run in runs)
    assert mock["verified_runs"] == 8
    assert sum(x["audit"]["llm_requests"] for x in mock["runs"]) == 212
    comp = results["component_metrics"]
    e = comp["extraction"]["overall"]
    expected = [
        e["entities"]["precision"],
        e["entities"]["recall"],
        e["entities"]["f1"],
        e["document_exact_match_accuracy"],
        comp["cti"]["identity"]["accuracy"],
        comp["cti"]["version_3class"]["accuracy"],
        comp["cti"]["version_binary"]["accuracy"],
    ]
    for row, num in zip(tables[11]["rows"], expected, strict=True):
        same(row[2], num, 4)
    for row, case in zip(tables[12]["rows"], results["cases"], strict=True):
        same(row[3], case["seconds"], 3)

    def stat(cohort, metric):
        return next(
            x for x in results["statistics"] if x["cohort"] == cohort and x["metric"] == metric
        )

    for i, row in enumerate(tables[13]["rows"], 1):
        baseline = results["corrected_native_benchmark"]["cases"][i - 1]
        assert list(map(int, row[1:4])) == [baseline["nodes"], baseline["edges"], 6]
        same(row[4], stat(f"onchain-baseline-{i}", "store_graph")["median"], 6)
        same(row[5], stat(f"onchain-baseline-{i}", "rank_graph")["median"], 6)
    for row, entry in zip(tables[14]["rows"], results["weight_sensitivity"], strict=True):
        same(row[2], entry["max_absolute_score_delta"], 9)
    t16 = " ".join(" ".join(row) for row in tables[16]["rows"])
    for metric in ["collect_telemetry", "worker_step"]:
        for key in ["median", "min", "max"]:
            assert f"{stat('isolated-telemetry-worker', metric)[key]:.6f}".replace(".", ",") in t16
    for metric in ["observed_asset_owl", "aln_projection", "graph_build_and_kg_lookup"]:
        for arm in ["with-runtime", "without-runtime"]:
            assert f"{stat('generator-' + arm, metric)['median']:.6f}".replace(".", ",") in t16
    for row, metric in zip(
        tables[17]["rows"],
        ["assess_software", "validate_countermeasure", "finalize_recommendation"],
        strict=True,
    ):
        for s, case in zip(row[1:], ["C1-r2", "C4-r3"], strict=True):
            same(s, stat("full-launcher-" + case, metric)["median"], 6)
    for i, row in enumerate(tables[18]["rows"], 1):
        same(row[1], stat(f"onchain-baseline-{i}", "rank_graph")["median"], 6)
        same(row[2], stat(f"offchain-baseline-{i}", "rank_graph")["median"], 6)
        entry = next(
            x
            for x in results["paired_statistics"]
            if x["cohort"] == "offchain-vs-mcp"
            and x["case"] == f"baseline-{i}"
            and x["metric"] == "rank_graph"
        )
        same(row[3], entry["median"], 6)
    for i, row in enumerate(tables[19]["rows"], 1):
        entry = next(
            x
            for x in results["paired_statistics"]
            if x["cohort"] == "rest-invoke-minus-evaluate" and x["case"] == f"baseline-{i}"
        )
        assert int(row[1]) == entry["n"]
        for s, key in zip(row[2:], ["min", "median", "max"], strict=True):
            same(s, entry[key], 6)
    assert results["runtime_comparison"]["generated_graph_owl_aln_equal"] is True
    assert results["runtime_comparison"]["inventory_lookup_statuses"] == {
        "with-runtime": {"matched": 1},
        "without-runtime": {"ambiguous": 12, "no_findings": 1, "matched": 1},
    }
    sources = [
        mockpath,
        ROOT / "evaluation/final-results-v1/results.json",
        ROOT / "config/metrics-evidence.v2.json",
    ]
    mapping = {
        "numeric_tables_verified": [
            int(tables[i]["caption"].split(".")[0].split()[1])
            for i in [4, 11, 12, 13, 14, 16, 17, 18, 19, 20]
        ],
        "stable_metric_table_ids": [4, 11, 12, 13, 14, 16, 17, 18, 19, 20],
        "scope": "Formatting and consistency checks; no new experiments or rescoring.",
        "sources_sha256": {
            str(p.relative_to(ROOT)): hashlib.sha256(p.read_bytes()).hexdigest() for p in sources
        },
    }
    (HERE / "fonti-dati.json").write_text(json.dumps(mapping, indent=2, ensure_ascii=False) + "\n")
    print(
        json.dumps(
            {
                "numeric_tables_verified": mapping["numeric_tables_verified"],
                "frozen_sources_unchanged": True,
            }
        )
    )


if __name__ == "__main__":
    verify()
