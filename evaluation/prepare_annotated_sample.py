"""Prepare source-based annotation drafts offline; never run the system under evaluation."""

from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import json
import re
import sqlite3
from collections import Counter
from pathlib import Path

from collect_inventory import sha

ROOT = Path(__file__).resolve().parents[1]
DEFAULT = ROOT / "evaluation/annotated-sample-v1"
OWL_SHA = "0ffa87d0ff610cd7860dc3cae4bd84e65ab223569ba19ef2f4240fba6da59350"
DB_SHA = "e3566009408385c7aea7901a9e6499132f0ae4bb07ccbd80d22e2171e5f7990c"
SOURCE_DIRS = {
    "logback_vulnerable": "output/case-improvements-20261106/sources/vulnerable",
    "logback_negative": "output/case-improvements-20261106/sources/negative",
    "log4j_vulnerable": "output/real-cases-20261105-r1/sources/vulnerable",
    "log4j_negative": "output/real-cases-20261105-r1/sources/negative",
}


def read(path):
    return json.loads(path.read_text())


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x", encoding="utf-8") as stream:
        json.dump(value, stream, indent=2, ensure_ascii=False, allow_nan=False)
        stream.write("\n")


def collect_owl(path):
    selected = (b"CVE-2026-1225", b"CVE-2025-68161", b"CVE-2026-34477")
    digest = hashlib.sha256()
    rows = []
    with path.open("rb") as stream:
        for number, line in enumerate(stream, 1):
            digest.update(line)
            if line.startswith(
                (b"DataPropertyAssertion(", b"ObjectPropertyAssertion(", b"ClassAssertion(")
            ) and any(x in line for x in selected):
                if len(line) < 8000:
                    rows.append({"line": number, "axiom": line.decode().rstrip("\n")})
    if digest.hexdigest() != OWL_SHA:
        raise ValueError("Original OWL differs from the frozen source")
    return {
        "source": str(path),
        "sha256": OWL_SHA,
        "size_bytes": path.stat().st_size,
        "selection": "Single-line assertions for three CVEs; not a complete CVE record.",
        "axioms": rows,
    }


def collect_rows(database, annotations):
    if Path(str(database) + "-wal").exists() and Path(str(database) + "-wal").stat().st_size:
        raise ValueError("Use the checkpointed frozen database, not a live WAL")
    if sha(database) != DB_SHA:
        raise ValueError("Database differs from the frozen source")
    product_ids = sorted(
        {
            row["source_product_id"]
            for row in annotations["matching_and_versions"]
            if row["source_product_id"] is not None
        }
    )
    with sqlite3.connect(database.resolve().as_uri() + "?mode=ro", uri=True) as connection:
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA query_only=ON")
        products = [
            dict(connection.execute("SELECT * FROM affected_product WHERE id=?", (key,)).fetchone())
            for key in product_ids
        ]
        versions = [
            dict(row)
            for key in product_ids
            for row in connection.execute(
                "SELECT * FROM affected_version WHERE affected_product_id=? ORDER BY id", (key,)
            )
        ]
        changes = [
            dict(row)
            for version in versions
            for row in connection.execute(
                "SELECT * FROM affected_version_change WHERE affected_version_id=? ORDER BY id",
                (version["id"],),
            )
        ]
        generic = [
            dict(row)
            for row in connection.execute(
                "SELECT DISTINCT vendor,product FROM affected_product WHERE product='logback' "
                "ORDER BY vendor,product"
            )
        ]
        unknown_count = connection.execute(
            "SELECT count(*) FROM affected_product WHERE product=?",
            ("thesis-unlisted-component-9f73",),
        ).fetchone()[0]
        vendor_count = connection.execute(
            "SELECT count(*) FROM affected_product WHERE vendor=? AND product=?",
            ("Thesis Example Vendor", "Logback-core"),
        ).fetchone()[0]
    if sha(database) != DB_SHA:
        raise ValueError("Database changed while reading")
    return {
        "database": str(database),
        "database_sha256": DB_SHA,
        "access": "sqlite3 mode=ro, query_only; raw rows, no matcher/evaluator imports",
        "products": products,
        "versions": versions,
        "version_changes": changes,
        "generic_logback_identities": generic,
        "unlisted_exact_product_count": unknown_count,
        "wrong_vendor_exact_identity_count": vendor_count,
    }


def compare_owl_rows(excerpt, rows):
    literals = {}
    for item in excerpt["axioms"]:
        match = re.fullmatch(r'DataPropertyAssertion\(:([^ ]+) :([^ ]+) (".*")\)', item["axiom"])
        if match:
            literals[(match[1], match[2])] = (json.loads(match[3]), item["line"])
    comparisons = []
    for collection, iri_key, properties in [
        (
            rows["products"],
            "affected_iri",
            {
                "vendor": "hasVendor",
                "product": "hasProduct",
                "package_name": "hasPackageName",
                "default_status": "hasDefaultStatus",
            },
        ),
        (
            rows["versions"],
            "version_iri",
            {
                "version": "hasVersion",
                "status": "hasStatus",
                "version_type": "hasVersionType",
                "less_than": "hasLessThan",
                "less_than_or_equal": "hasLessThanOrEqual",
            },
        ),
    ]:
        for row in collection:
            for field, prop in properties.items():
                if row[field] is not None:
                    value, line = literals[(prop, row[iri_key])]
                    if value != row[field]:
                        raise ValueError(f"Raw OWL/SQLite mismatch: {row[iri_key]} {prop}")
                    comparisons.append(
                        {
                            "table_id": row["id"],
                            "individual": row[iri_key],
                            "field": field,
                            "value": value,
                            "owl_line": line,
                        }
                    )
    return comparisons


def documents(raw):
    return [json.loads(line) for line in raw.decode().splitlines() if line.strip()]


def make_input(case, sources):
    transform = case["transformation"]
    if transform == "none":
        return sources[case["source"]]
    if transform == "bundle_two_original_records":
        values = [documents(sources[key])[0] for key in ("logback_vulnerable", "log4j_vulnerable")]
    else:
        values = [copy.deepcopy(documents(sources[case["source"]])[0])]
        resource = values[0]["resourceLogs"][0]
        attrs = resource["resource"]["attributes"]
        if transform == "add_explicit_vendor":
            attrs.append({"key": "thesis.software.vendor", "value": {"stringValue": "QOS.CH Sarl"}})
        elif transform == "remove_version":
            attrs[:] = [a for a in attrs if a["key"] != "thesis.software.version"]
        elif transform in {
            "orphan_version_only",
            "remove_software_attributes",
            "planned_dependency_only",
        }:
            attrs[:] = [
                a
                for a in attrs
                if not a["key"].startswith("thesis.software.")
                or (transform == "orphan_version_only" and a["key"] == "thesis.software.version")
            ]
            if transform == "planned_dependency_only":
                resource["scopeLogs"][0]["logRecords"][0]["body"] = {
                    "stringValue": "Planned dependency: logback-core 1.5.24; "
                    "not loaded in this event."
                }
        elif transform == "degrade_product_name":
            next(a for a in attrs if a["key"] == "thesis.software.name")["value"] = {
                "stringValue": "logback"
            }
        elif transform == "non_string_version":
            next(a for a in attrs if a["key"] == "thesis.software.version")["value"] = {
                "intValue": "1524"
            }
        else:
            raise ValueError(f"Unsupported declared transformation: {transform}")
    return (
        "".join(json.dumps(doc, ensure_ascii=False, separators=(",", ":")) + "\n" for doc in values)
    ).encode()


def evidence_spans(case, raw):
    candidates = []
    for line, doc in enumerate(documents(raw), 1):
        for ri, resource in enumerate(doc["resourceLogs"]):
            attrs = resource["resource"]["attributes"]
            values = {a["key"]: a["value"].get("stringValue") for a in attrs}
            for ei, entity in enumerate(case["expected_entities"]):
                if values.get("thesis.software.name") != entity["product"]:
                    continue
                for field, key in (
                    ("product", "name"),
                    ("version", "version"),
                    ("vendor", "vendor"),
                ):
                    if entity[field] is None:
                        continue
                    name = "thesis.software." + key
                    index = next(i for i, a in enumerate(attrs) if a["key"] == name)
                    actual = attrs[index]["value"].get("stringValue")
                    if actual != entity[field]:
                        raise ValueError(f"Gold literal absent from input: {case['id']} {field}")
                    candidates.append(
                        {
                            "case_id": case["id"],
                            "entity_index": ei,
                            "field": field,
                            "value": actual,
                            "line": line,
                            "pointer": f"/resourceLogs/{ri}/resource/attributes/"
                            f"{index}/value/stringValue",
                        }
                    )
    for index, entity in enumerate(case["expected_entities"]):
        for field, value in entity.items():
            if value is not None and not any(
                r["entity_index"] == index and r["field"] == field for r in candidates
            ):
                raise ValueError(f"No source span for {case['id']} entity {index} {field}")
    return candidates


def check(directory):
    manifest = read(directory / "manifest.json")
    for name, expected in manifest["files_sha256"].items():
        if sha(directory / name) != expected:
            raise ValueError(f"Sample changed after preparation: {name}")
    annotation = read(directory / "annotations.json")
    ids = [
        row["id"]
        for section in ("extraction", "matching_and_versions")
        for row in annotation[section]
    ]
    if len(ids) != 28 or len(set(ids)) != len(ids):
        raise ValueError("Expected 28 distinct cases")
    for span in read(directory / "evidence-spans.json"):
        raw = (directory / "inputs" / (span["case_id"] + ".otel.jsonl")).read_bytes()
        value = documents(raw)[span["line"] - 1]
        for token in span["pointer"].strip("/").split("/"):
            value = value[int(token)] if isinstance(value, list) else value[token]
        if value != span["value"]:
            raise ValueError("Evidence pointer does not resolve to annotated literal")
    with (directory / "review.csv").open(newline="") as stream:
        review = list(csv.DictReader(stream))
    if sorted(r["case_id"] for r in review) != sorted(ids):
        raise ValueError("Review sheet does not cover all cases")
    if annotation["human_review_completed"] or annotation["predictions_collected"]:
        raise ValueError("This v1 is a draft, not a human-approved scored dataset")
    metrics = read(directory / "metrics-template.json")
    if not all(value is None for value in metrics["values"].values()):
        raise ValueError("Do not attach uncollected scores to the preparation draft")
    print(
        json.dumps(
            {
                "files_verified": len(manifest["files_sha256"]),
                "cases": len(ids),
                "status": annotation["status"],
                "evaluation_ready": False,
                **read(directory / "summary.json"),
            },
            indent=2,
        )
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--directory", type=Path, default=DEFAULT)
    parser.add_argument(
        "--database",
        type=Path,
        default=Path.home() / "Desktop/agent-based-cti-argumentation-pipeline/app/data/"
        "cve2owl_20260523_143950.affected.sqlite",
    )
    parser.add_argument(
        "--owl", type=Path, default=Path.home() / "Downloads/cve2owl_20260523_143950.owl"
    )
    parser.add_argument("--verified-excerpt", type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    directory = args.directory.resolve()
    if args.check:
        check(directory)
        return
    if (directory / "manifest.json").exists():
        parser.error("Do not overwrite a prepared sample; use a new draft directory")
    annotation = read(directory / "annotations.json")
    excerpt = read(args.verified_excerpt) if args.verified_excerpt else collect_owl(args.owl)
    if excerpt["sha256"] != OWL_SHA or args.owl.stat().st_size != excerpt["size_bytes"]:
        raise ValueError("Excerpt does not refer to the frozen original OWL")
    rows = collect_rows(args.database, annotation)
    comparisons = compare_owl_rows(excerpt, rows)
    sources, source_manifest = {}, {}
    for key, relative in SOURCE_DIRS.items():
        source = ROOT / relative
        manifest = read(source / "source_manifest.json")
        for name, expected in manifest["files"].items():
            if sha(source / name) != expected:
                raise ValueError(f"Original source changed: {relative}/{name}")
        raw = (source / "otel.jsonl").read_bytes()
        sources[key] = raw
        path = directory / "sources" / (key + ".otel.jsonl")
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("xb") as stream:
            stream.write(raw)
        write(directory / "sources" / (key + ".build.json"), manifest)
        source_manifest[key] = {
            "original_directory": relative,
            "otel_sha256": sha(path),
            "record_count": len(documents(raw)),
            "source_manifest_sha256": sha(source / "source_manifest.json"),
        }
    write(directory / "sources/owl-excerpt.json", excerpt)
    write(directory / "sources/raw-kg-rows.json", rows)
    write(directory / "sources/owl-sqlite-comparisons.json", comparisons)
    write(directory / "sources/originals.json", source_manifest)
    spans = []
    for case in annotation["extraction"]:
        raw = make_input(case, sources)
        target = directory / case["input"]
        target.parent.mkdir(parents=True, exist_ok=True)
        with target.open("xb") as stream:
            stream.write(raw)
        spans.extend(evidence_spans(case, raw))
    write(directory / "evidence-spans.json", spans)
    with (directory / "inputs/cti-queries.jsonl").open("x") as stream:
        for case in annotation["matching_and_versions"]:
            stream.write(
                json.dumps(
                    {
                        "id": case["id"],
                        "software": case["query"],
                        "evidence_id": "annotated-v1:" + case["id"],
                    }
                )
                + "\n"
            )
    with (directory / "review.csv").open("x", newline="", encoding="utf-8") as stream:
        fields = [
            "case_id",
            "task",
            "expected",
            "rationale",
            "review_status",
            "reviewer",
            "reviewed_at",
            "correction",
            "notes",
        ]
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for section in ("extraction", "matching_and_versions"):
            for case in annotation[section]:
                expected = case.get(
                    "expected_entities",
                    {
                        "identity_status": case.get("identity_status"),
                        "identity_refs": case.get("identity_refs"),
                        "cve_id": case.get("cve_id"),
                        "version_label": case.get("version_label"),
                    },
                )
                writer.writerow(
                    {
                        "case_id": case["id"],
                        "task": section,
                        "expected": json.dumps(expected, ensure_ascii=False),
                        "rationale": case["rationale"],
                        "review_status": "pending",
                    }
                )
    labels = Counter(c["version_label"] for c in annotation["matching_and_versions"])
    summary = {
        "extraction_documents": len(annotation["extraction"]),
        "original_runtime_builds": 4,
        "original_sdk_documents": 4,
        "controlled_derivative_documents": 8,
        "gold_entities": sum(len(c["expected_entities"]) for c in annotation["extraction"]),
        "negative_extraction_documents": sum(
            not c["expected_entities"] for c in annotation["extraction"]
        ),
        "matching_queries": len(annotation["matching_and_versions"]),
        "version_labels": dict(labels),
        "version_accuracy_3class_denominator": sum(
            labels[x] for x in ("vulnerable", "not_vulnerable", "unknown")
        ),
        "version_accuracy_binary_denominator": labels["vulnerable"] + labels["not_vulnerable"],
        "raw_owl_sqlite_fields_checked": len(comparisons),
        "human_review_completed": False,
        "predictions_collected": False,
    }
    write(directory / "summary.json", summary)
    write(
        directory / "metrics-template.json",
        {
            "status": "not_measured_pending_review_and_predictions",
            "values": {
                key: None
                for key in (
                    "precision",
                    "recall",
                    "f1",
                    "document_exact_match_accuracy",
                    "product_matching_accuracy",
                    "version_accuracy_3class",
                    "version_accuracy_binary",
                )
            },
        },
    )
    write(
        directory / "manifest.json",
        {
            "contract": "independent-annotation-manifest-v1",
            "date": "2026-11-12",
            "preparer_sha256": sha(Path(__file__)),
            "system_under_evaluation_executed": False,
            "network_or_services_contacted": False,
            "prediction_artifacts_used_as_labels": False,
            "frozen_owl_sha256": OWL_SHA,
            "frozen_database_sha256": DB_SHA,
            "files_sha256": {
                p.relative_to(directory).as_posix(): sha(p)
                for p in sorted(directory.rglob("*"))
                if p.is_file()
            },
        },
    )
    check(directory)


if __name__ == "__main__":
    main()
