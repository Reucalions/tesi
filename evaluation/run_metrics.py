"""Collect existing component outputs, then score against a frozen assisted reference.

Collection reads only input files and their manifest; annotations are opened only
by the separate score command, after prediction artifacts have been written.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import sys
import time
import unicodedata
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
DEFAULT_SAMPLE = ROOT / "evaluation/annotated-sample-v2"
DATASET_SHA = "e3566009408385c7aea7901a9e6499132f0ae4bb07ccbd80d22e2171e5f7990c"


def read(path):
    return json.loads(path.read_text())


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write("\n")


def verify_sample(sample):
    manifest = read(sample / "manifest.json")
    if not manifest.get("evaluation_ready_for_controlled_assisted_study"):
        raise ValueError("Use the frozen source-reviewed reference")
    for name, digest in manifest["files_sha256"].items():
        if sha(sample / name) != digest:
            raise ValueError(f"Frozen sample changed: {name}")
    return sha(sample / "manifest.json")


def normal(value):
    return unicodedata.normalize("NFC", value).strip().casefold() if value is not None else None


def entity(value):
    return (
        normal(value["product"]),
        value.get("version", "").strip() if value.get("version") is not None else None,
        normal(value.get("vendor")),
    )


def ratio(numerator, denominator):
    return numerator / denominator if denominator else None


def counts(reference, predicted):
    return {
        "tp": len(reference & predicted),
        "fp": len(predicted - reference),
        "fn": len(reference - predicted),
    }


def prf(values):
    tp, fp, fn = (values[k] for k in ("tp", "fp", "fn"))
    return {
        **values,
        "precision": ratio(tp, tp + fp),
        "recall": ratio(tp, tp + fn),
        "f1": ratio(2 * tp, 2 * tp + fp + fn),
    }


def field_facts(entities):
    # This corpus has distinct product names per document. Anchor each field to
    # its product, never combine name/version/vendor from different resources.
    return {
        (product, field, value)
        for product, version, vendor in entities
        for field, value in (("product", product), ("version", version), ("vendor", vendor))
        if value is not None
    }


def score_extraction(cases, predictions):
    rows = []
    for case in cases:
        pred = predictions[case["id"]]
        reference = {entity(e) for e in case["expected_entities"]}
        actual = {entity(e) for e in pred["entities"]} if pred["status"] == "ok" else set()
        rows.append(
            {
                "id": case["id"],
                "kind": case["kind"],
                "status": pred["status"],
                "reference_entities": len(reference),
                "predicted_entities": len(actual),
                **counts(reference, actual),
                "document_correct": pred["status"] == "ok" and reference == actual,
                "field_counts": counts(field_facts(reference), field_facts(actual)),
            }
        )

    def aggregate(selected):
        total = {key: sum(r[key] for r in selected) for key in ("tp", "fp", "fn")}
        fields = {key: sum(r["field_counts"][key] for r in selected) for key in ("tp", "fp", "fn")}
        correct = sum(r["document_correct"] for r in selected)
        return {
            "documents": len(selected),
            "technical_errors": sum(r["status"] != "ok" for r in selected),
            "entities": prf(total),
            "fields": prf(fields),
            "document_exact_match_correct": correct,
            "document_exact_match_accuracy": ratio(correct, len(selected)),
        }

    return {
        "overall": aggregate(rows),
        "original_sdk": aggregate([r for r in rows if r["kind"] == "original_sdk"]),
        "controlled_derivatives": aggregate(
            [r for r in rows if r["kind"] == "controlled_synthetic_derivative"]
        ),
        "cases": rows,
    }


def predicted_identity(assessment):
    # Same resolution condition used by thesis_agents.tools.cti_mcp.map_assessment.
    matches = assessment["matching"]["matches"]
    if not matches:
        return "not_found", []
    identities = [(normal(m["vendor"]), normal(m["product"])) for m in matches]
    resolved = len(matches) == 1 and matches[0]["confidence"] == "high"
    return ("matched" if resolved else "ambiguous"), identities


def score_cti_case(case, references, prediction):
    eligible_version = case["version_label"] != "not_evaluable"
    binary = case["version_label"] in {"vulnerable", "not_vulnerable"}
    row = {
        "id": case["id"],
        "status": prediction["status"],
        "policy_case": case["id"] in {"C08", "C11", "C16"},
        "expected_identity_status": case["identity_status"],
        "expected_version": case["version_label"],
        "version_eligible": eligible_version,
        "binary_eligible": binary,
        "predicted_identity_status": "technical_error",
        "identity_correct": False,
        "predicted_version": "technical_error",
        "version_correct": False,
        "raw_version_statuses": [],
        "resolved_identity": None,
    }
    if prediction["status"] != "ok":
        return row
    assessment = prediction["assessment"]
    status, identities = predicted_identity(assessment)
    expected = {
        (normal(references[key]["vendor"]), normal(references[key]["product"]))
        for key in case["identity_refs"]
    }
    correct = status == case["identity_status"] and (
        set(identities) == expected
        if status == "matched"
        else expected <= set(identities)
        if status == "ambiguous"
        else not identities
    )
    row.update(
        predicted_identity_status=status,
        identity_correct=correct,
        resolved_identity=identities[0] if status == "matched" else None,
        predicted_version="identity_unresolved" if status != "matched" else "wrong_identity",
    )
    if not eligible_version or not correct or status != "matched":
        return row
    entries = [
        entry
        for asset in assessment["assessment"]["results"]
        for match in asset["matches"]
        for entry in match["affected_entries"]
        if entry["cve_id"] == case["cve_id"]
        and (normal(match["vendor"]), normal(match["product"])) in expected
    ]
    statuses = [entry["vulnerability_status"] for entry in entries]
    row["raw_version_statuses"] = statuses
    if not statuses:
        label = "missing_cve_assessment"
    elif "vulnerable" in statuses:
        label = "vulnerable"
    elif all(s == "not_vulnerable" for s in statuses):
        label = "not_vulnerable"
    elif all(s in {"unknown", "not_evaluable", "skipped", "not_vulnerable"} for s in statuses):
        label = "unknown"
    else:
        label = "invalid_cve_assessment"
    row.update(predicted_version=label, version_correct=label == case["version_label"])
    return row


def score_cti(cases, references, predictions):
    rows = [score_cti_case(c, references, predictions[c["id"]]) for c in cases]

    def accuracy(selected, key):
        correct = sum(r[key] for r in selected)
        return {
            "correct": correct,
            "denominator": len(selected),
            "accuracy": ratio(correct, len(selected)),
        }

    version = [r for r in rows if r["version_eligible"]]
    binary = [r for r in rows if r["binary_eligible"]]
    confusion = Counter((r["expected_version"], r["predicted_version"]) for r in version)
    return {
        "identity": accuracy(rows, "identity_correct"),
        "identity_direct_cases": accuracy(
            [r for r in rows if not r["policy_case"]], "identity_correct"
        ),
        "identity_policy_cases": accuracy(
            [r for r in rows if r["policy_case"]], "identity_correct"
        ),
        "version_3class": accuracy(version, "version_correct"),
        "version_binary": accuracy(binary, "version_correct"),
        "technical_errors": sum(r["status"] != "ok" for r in rows),
        "version_confusion": [
            {"expected": k[0], "predicted": k[1], "count": v} for k, v in sorted(confusion.items())
        ],
        "cases": rows,
    }


def collect(sample, output, url):
    # Imports below are the real production components, not a replacement parser.
    from services.otel_gateway.server import identify
    from thesis_agents.mcp.cti_contracts import SoftwareQuery
    from thesis_agents.mcp.cti_probe import run_probe
    from thesis_agents.mcp.settings import MCPSettings

    sample_digest = verify_sample(sample)
    output.mkdir(parents=True, exist_ok=False)
    code_paths = [
        Path(__file__),
        ROOT / "services/otel_gateway/server.py",
        ROOT / "thesis_agents/mcp/cti_probe.py",
        ROOT / "thesis_agents/mcp/cti_client.py",
        ROOT / "thesis_agents/tools/cti_mcp.py",
    ]
    write(
        output / "protocol.json",
        {
            "reference_date": "2026-11-12",
            "sample_manifest_sha256": sample_digest,
            "collector_and_scorer_sha256": sha(Path(__file__)),
            "code_sha256": {str(p.relative_to(ROOT)): sha(p) for p in code_paths},
            "cti_url": url,
            "dataset_sha256": DATASET_SHA,
            "extraction": "Existing OTel identify(resource,record), all records, unique tuples; "
            "component only, no CAMEL or LangExtract inference or window filtering.",
            "identity_resolution": "Exactly one returned candidate with high confidence; "
            "same as "
            "the framework mapper. Zero candidates=not_found, otherwise ambiguous.",
            "ambiguous_scoring": "Require the reference identities among candidates; "
            "extra diagnostic "
            "candidates allowed, no resolved identity.",
            "version": "Only successful calls with correctly resolved identity; "
            "target CVE selected "
            "after collection. Missing target or technical error is incorrect, not unknown.",
            "version_status_projection": "vulnerable dominates; "
            "all not_vulnerable => not_vulnerable; "
            "unknown/not_evaluable/skipped => unknown when target exists.",
            "denominators": {
                "extraction_documents": 12,
                "identity": 16,
                "version_3class": 13,
                "version_binary": 8,
            },
            "annotations_parsed_by_collector": False,
            "annotation_bytes_hashed_for_integrity_only": True,
            "llm_used": False,
            "fabric_used": False,
            "new_frozen_collection": True,
        },
    )
    predictions = {"extraction": {}, "cti": {}}
    for path in sorted((sample / "inputs").glob("E*.otel.jsonl")):
        started = time.monotonic()
        raw_records = []
        result = {"status": "ok", "entities": [], "input_sha256": sha(path)}
        try:
            for line in path.read_text().splitlines():
                for resource in json.loads(line)["resourceLogs"]:
                    for scope in resource.get("scopeLogs", []):
                        for record in scope.get("logRecords", []):
                            identity = identify(resource["resource"], record)
                            raw_records.append(identity)
            unique = {
                (i["package"], i["version"], i.get("vendor")) for i in raw_records if i is not None
            }
            result["entities"] = [
                {"product": p, "version": v, "vendor": vendor} for p, v, vendor in sorted(unique)
            ]
        except Exception as error:
            result.update(status="technical_error", error_type=type(error).__name__)
        result.update(elapsed_seconds=time.monotonic() - started, raw_identities=raw_records)
        key = path.name.split(".")[0]
        write(output / "predictions/extraction" / (key + ".json"), result)
        predictions["extraction"][key] = result
        print(f"extraction {key}: {result['status']}", flush=True)
    settings = MCPSettings(url=url, expected_kind="real", timeout_seconds=60)
    for line in (sample / "inputs/cti-queries.jsonl").read_text().splitlines():
        query = json.loads(line)
        started = time.monotonic()
        result = {"status": "technical_error"}
        try:
            software = SoftwareQuery(**query["software"], evidence_id=query["evidence_id"])
            response = run_probe(settings, software, output / "predictions/cti" / query["id"])
            if response.dataset.sha256 != DATASET_SHA:
                raise ValueError("Unexpected dataset digest")
            result = {"status": "ok", "assessment": response.model_dump(mode="json")}
        except Exception as error:
            result["error_type"] = type(error).__name__
        result["elapsed_seconds"] = time.monotonic() - started
        write(output / "predictions/cti" / (query["id"] + ".json"), result)
        predictions["cti"][query["id"]] = result
        print(f"cti {query['id']}: {result['status']}", flush=True)
    if verify_sample(sample) != sample_digest:
        raise ValueError("Sample changed during collection")
    write(output / "predictions.json", predictions)
    write(
        output / "collection-manifest.json",
        {
            "sample_manifest_sha256": sample_digest,
            "files_sha256": {
                p.relative_to(output).as_posix(): sha(p)
                for p in sorted(output.rglob("*"))
                if p.is_file()
            },
            "annotations_parsed": False,
            "annotation_bytes_hashed_for_integrity_only": True,
            "llm_used": False,
            "fabric_used": False,
        },
    )


def score(sample, output):
    if (output / "metrics.json").exists():
        raise ValueError("Existing scores are immutable; use a separate collection")
    protocol = read(output / "protocol.json")
    if verify_sample(sample) != protocol["sample_manifest_sha256"]:
        raise ValueError("Sample differs from collection")
    if sha(Path(__file__)) != protocol["collector_and_scorer_sha256"]:
        raise ValueError("Scorer changed after collection; preserve the original implementation")
    for name, digest in read(output / "collection-manifest.json")["files_sha256"].items():
        if sha(output / name) != digest:
            raise ValueError(f"Prediction artifact changed: {name}")
    annotation = read(sample / "annotations.json")
    predictions = read(output / "predictions.json")
    references = {r["id"]: r for r in annotation["identity_references"]}
    extraction = score_extraction(annotation["extraction"], predictions["extraction"])
    cti = score_cti(annotation["matching_and_versions"], references, predictions["cti"])
    if (
        extraction["overall"]["documents"],
        cti["identity"]["denominator"],
        cti["version_3class"]["denominator"],
        cti["version_binary"]["denominator"],
    ) != (12, 16, 13, 8):
        raise ValueError("Unexpected metric denominators")
    metrics = {
        "reference_date": "2026-11-12",
        "scope": "Existing component benchmark, "
        "assisted source-reviewed reference; not a full agent or Fabric run.",
        "human_reference_review": False,
        "llm_used": False,
        "extraction": extraction,
        "cti": cti,
    }
    write(output / "metrics.json", metrics)
    for name, rows in (
        ("extraction-cases.csv", extraction["cases"]),
        ("cti-cases.csv", cti["cases"]),
    ):
        with (output / name).open("x", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
            writer.writeheader()
            for row in rows:
                writer.writerow(
                    {
                        k: json.dumps(v, ensure_ascii=False) if isinstance(v, (dict, list)) else v
                        for k, v in row.items()
                    }
                )
    write(
        output / "results-manifest.json",
        {
            "sample_manifest_sha256": protocol["sample_manifest_sha256"],
            "scorer_sha256": sha(Path(__file__)),
            "files_sha256": {
                p.relative_to(output).as_posix(): sha(p)
                for p in sorted(output.rglob("*"))
                if p.is_file()
            },
        },
    )
    print(
        json.dumps(
            {
                "extraction": extraction["overall"],
                "matching": cti["identity"],
                "version_3class": cti["version_3class"],
                "version_binary": cti["version_binary"],
                "cti_technical_errors": cti["technical_errors"],
            },
            indent=2,
        )
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=("collect", "score"))
    parser.add_argument("--sample", type=Path, default=DEFAULT_SAMPLE)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--cti-url", default="http://127.0.0.1:18043/mcp")
    args = parser.parse_args()
    if args.action == "collect":
        collect(args.sample.resolve(), args.output.resolve(), args.cti_url)
    else:
        score(args.sample.resolve(), args.output.resolve())


if __name__ == "__main__":
    main()
