"""Verify displayed C1 semantic extracts against immutable evidence from the same run."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]


def blocks(text, operator):
    result = []
    offset = 0
    while (start := text.find(operator + "(", offset)) >= 0:
        depth = 0
        for end in range(start + len(operator), len(text)):
            depth += (text[end] == "(") - (text[end] == ")")
            if depth == 0:
                result.append(text[start : end + 1])
                offset = end + 1
                break
        else:
            raise ValueError("Unbalanced semantic expression")
    return result


def verify():
    data = json.loads((HERE / "esempio-semantico.json").read_text())
    content = json.loads((HERE / "contenuto.json").read_text())
    tables = {
        b["semantic_table_id"]: b
        for page in content["pages"]
        for b in page["blocks"]
        if b["type"] == "table" and "semantic_table_id" in b
    }
    for relative, expected in data["sources_sha256"].items():
        assert hashlib.sha256((ROOT / relative).read_bytes()).hexdigest() == expected, relative
    assert len(data["dag_nodes"]) == 8
    assert all(node["status"] == "completed" for node in data["dag_nodes"].values())
    assert data["otel_observations"] == 5
    assert data["unobserved_flags"] == {"endpoint_exposed": None, "deserialization_observed": None}
    rule = data["version_rules"][0]
    assert rule["version"] == "0.9.20" and rule["less_than_or_equal"] == "1.5.24"
    assert rule["evaluated"] and rule["matched_asset_version"]
    assert data["osv_advisories"][0]["matched_cves"] == ["CVE-2026-1225"]
    assert data["osv_advisories"][0]["ranges"][0]["events"][1]["fixed"] == "1.5.25"
    expected_aliases = [[key, uri.rsplit("#", 1)[1]] for key, uri in data["aliases"].items()]
    assert tables["aliases"]["rows"] == expected_aliases
    alias = {key: uri.rsplit("#", 1)[1] for key, uri in data["aliases"].items()}
    for displayed, raw in [
        (
            "ClassAssertion(ObservedSoftwareAsset a)",
            f"ClassAssertion(:ObservedSoftwareAsset :{alias['a']})",
        ),
        (
            "ObjectPropertyAssertion(hasAffectedPackage a p)",
            f"ObjectPropertyAssertion(:hasAffectedPackage :{alias['a']} :{alias['p']})",
        ),
        (
            "ObjectPropertyAssertion(hasAffectedVersionStatement a v)",
            f"ObjectPropertyAssertion(:hasAffectedVersionStatement :{alias['a']} :{alias['v']})",
        ),
    ]:
        assert displayed in [row[0] for row in tables["owl"]["rows"]]
        assert raw in data["observed_owl"]
    assertions = blocks(data["aln"], "ClassAssertion")
    resource = next(x for x in assertions if x.endswith(":" + alias["r"] + "\n)"))
    normalized = re.sub(r"\s+", " ", re.sub(r"(?<![\w]):(?=[A-Za-z])", "", resource))
    for row in tables["aln"]["rows"]:
        for term in row[0].split(";"):
            assert term.strip() in normalized, term
    for axiom in [
        "SubClassOf(:Solutions :MitigationStrategy)",
        "SubClassOf(:MitigationStrategy :RankingArgument)",
    ]:
        assert axiom in data["aln"]
    assert data["vulnerability"]["cvss"] is None and data["vulnerability"]["cwe"] == []
    graph = data["graphs"][0]["ranking_request"]["graph"]
    assert len(graph["nodes"]) == 2
    assert graph["edges"] == [{"from": alias["c"], "to": alias["r"]}]
    rank = data["ranked"][0]
    assert rank["rank"] == 1 and rank["score"] == 1
    assert rank["explanation"]["method"] == "single_candidate_convention_v1"
    native = data["native"]
    assert native["abductionPenalty"] == 38 and native["score"] == 62
    assert data["affinity"] == 0.62 and data["semantic_status"] == "requires_prerequisites"
    assert data["bonus_evaluated"] is False
    assert native["contractionPenalty"] == 0 and not native["giveUp"] and not native["keep"]
    for term in [
        "Solutions",
        "TargetsProduct_Logback_core",
        "ForCVE_CVE_2026_1225",
        "hasAttackVector",
    ]:
        assert term in native["hypothesis"]
    op = data["operational_result"]
    assert op["missing_capabilities"] == [] and op["prohibited_action"] is False
    assert op["status"] == "requires_review" and len(op["unassessed_constraints"]) == 1
    assert set(data["operational_context"]["available_capabilities"]) == {
        "package_upgrade",
        "maintenance_window",
    }
    assert data["recommendation"]["selected_strategy_id"] is None
    assert data["recommendation"]["outcome"] == "requires_prerequisites"
    assert data["provenance_counts"] == {
        "entities": 16,
        "activities": 9,
        "agents": 11,
        "relations": 40,
    }
    assert len(data["source_digests"]) == 8
    locations = {
        "runtime_evidence": "sources/runtime_evidence.json",
        "vulnerability_report": "sources/vulnerability_report.json",
        "candidate_strategies": "sources/candidate_strategies.json",
        "canonical_preparation": "preparation/canonical_preparation.json",
        "native_strategic_ranking": "strategic/native_strategic_ranking.json",
        "native_strategic_validation": "validation/native_strategic_validation.json",
        "validation_profile": "validation/validation-profile.json",
        "native_strategic_recommendation": "recommendation/native_strategic_recommendation.json",
    }
    run = ROOT / "output/case-improvements-20261106/runs/C1-r2"
    for name, relative in locations.items():
        assert (
            "sha256:" + hashlib.sha256((run / relative).read_bytes()).hexdigest()
            == data["source_digests"][name]
        )
    prov = data["provenance"]

    def find(rows, part):
        return next(x["id"] for x in rows if part in x["id"])

    a_prep = find(prov["activities"], ":canonical_preparation:")
    e_runtime = find(prov["entities"], ":runtime_evidence:")
    a_val = find(prov["activities"], ":backend-validation-")
    tiny = find(prov["agents"], ":tinyme-reasoner")
    recommendation = find(prov["entities"], "urn:cti:recommendation:")
    a_sel = find(prov["activities"], ":native_strategic_recommendation:")
    for subject, predicate, obj in [
        (a_prep, "prov:used", e_runtime),
        (a_val, "prov:wasAssociatedWith", tiny),
        (recommendation, "prov:wasGeneratedBy", a_sel),
    ]:
        assert {"subject": subject, "predicate": predicate, "object": obj} in prov["relations"]
    assert data["commit"]["block_number"] == "22" and data["commit"]["validation_code"] == 0
    assert data["commit"]["successful"] and data["readback"]["record_provenance_receipt_identical"]
    assert data["readback"]["transaction_id"] == data["commit"]["transaction_id"]
    result = {
        "case": "C1",
        "source_files_sha256_verified": len(data["sources_sha256"]),
        "same_complete_run": True,
        "displayed_owl_assertions_verified": 3,
        "displayed_aln_rows_verified": len(tables["aln"]["rows"]),
        "source_digests_verified": 8,
        "displayed_prov_relations_verified": 3,
        "native_and_operational_results_verified": True,
        "ledger_readback_matches": True,
    }
    (HERE / "verifica-caso.json").write_text(json.dumps(result, indent=2) + "\n")
    print(json.dumps(result))


if __name__ == "__main__":
    verify()
