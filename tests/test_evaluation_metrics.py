"""Check metric definitions and error accounting without contacting the measured system."""

from evaluation.run_metrics import score_cti, score_cti_case, score_extraction


def cti_response(status="unknown", *, entries=True):
    identity = {"vendor": "Vendor", "product": "Product", "confidence": "high"}
    match = {
        **identity,
        "affected_entries": [{"cve_id": "CVE-2026-9999", "vulnerability_status": status}]
        if entries
        else [],
    }
    return {
        "status": "ok",
        "assessment": {
            "matching": {"matches": [identity]},
            "assessment": {"results": [{"matches": [match]}]},
        },
    }


def case(label="unknown"):
    return {
        "id": "C01",
        "identity_status": "matched",
        "identity_refs": ["I"],
        "cve_id": "CVE-2026-9999",
        "version_label": label,
    }


REFERENCES = {"I": {"vendor": "Vendor", "product": "Product"}}


def test_wrong_vendor_is_entity_fp_and_fn_but_fields_keep_their_meaning():
    reference = [
        {
            "id": "E01",
            "kind": "original_sdk",
            "expected_entities": [{"product": "Product", "version": "1", "vendor": "Vendor"}],
        }
    ]
    result = score_extraction(
        reference,
        {
            "E01": {
                "status": "ok",
                "entities": [{"product": "Product", "version": "1", "vendor": None}],
            }
        },
    )["overall"]
    assert result["entities"] == {"tp": 0, "fp": 1, "fn": 1, "precision": 0, "recall": 0, "f1": 0}
    assert result["fields"]["tp"] == 2 and result["fields"]["fn"] == 1
    assert result["document_exact_match_accuracy"] == 0


def test_empty_document_has_undefined_prf_and_error_is_not_exact_match():
    reference = [{"id": "E01", "kind": "original_sdk", "expected_entities": []}]
    for status, correct in [("ok", 1), ("technical_error", 0)]:
        result = score_extraction(reference, {"E01": {"status": status, "entities": []}})
        assert all(result["overall"]["entities"][k] is None for k in ["precision", "recall", "f1"])
        assert result["overall"]["document_exact_match_correct"] == correct


def test_unknown_domain_result_is_distinct_from_technical_error_and_missing_cve():
    assert score_cti_case(case(), REFERENCES, cti_response())["version_correct"]
    assert score_cti_case(case(), REFERENCES, cti_response("not_evaluable"))["version_correct"]
    for prediction in [{"status": "technical_error"}, cti_response(entries=False)]:
        assert not score_cti_case(case(), REFERENCES, prediction)["version_correct"]


def test_failed_matching_does_not_shrink_version_denominators():
    cases = [case(), {**case("vulnerable"), "id": "C02"}]
    predictions = {"C01": {"status": "technical_error"}, "C02": cti_response("vulnerable")}
    result = score_cti(cases, REFERENCES, predictions)
    assert result["identity"]["denominator"] == 2
    assert result["version_3class"] == {"correct": 1, "denominator": 2, "accuracy": 0.5}
    assert result["version_binary"] == {"correct": 1, "denominator": 1, "accuracy": 1}
    assert result["technical_errors"] == 1


def test_wrong_resolved_identity_cannot_pass_version_scoring():
    prediction = cti_response()
    prediction["assessment"]["matching"]["matches"][0]["vendor"] = "Different vendor"
    result = score_cti_case(case(), REFERENCES, prediction)
    assert not result["identity_correct"] and not result["version_correct"]
    assert result["predicted_version"] == "wrong_identity"


def test_ambiguity_requires_reference_candidates_and_never_becomes_resolved():
    reference = {**REFERENCES, "J": {"vendor": "Other", "product": "Product"}}
    candidate = {
        **case("not_evaluable"),
        "id": "C08",
        "identity_status": "ambiguous",
        "identity_refs": ["I", "J"],
    }
    prediction = cti_response()
    matches = prediction["assessment"]["matching"]["matches"]
    matches.extend(
        [
            {"vendor": "Other", "product": "Product", "confidence": "high"},
            {"vendor": "Diagnostic", "product": "Candidate", "confidence": "medium"},
        ]
    )
    assert score_cti_case(candidate, reference, prediction)["identity_correct"]
    matches.pop(1)
    assert not score_cti_case(candidate, reference, prediction)["identity_correct"]
