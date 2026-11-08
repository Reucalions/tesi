"""Independent qualitative expectations; no replacement ranking or DL reasoner."""

import importlib.util
import json
from pathlib import Path

import pytest

from thesis_agents.mcp.shared_contracts import SharedValidation

PIPELINE = Path("/Users/reucalion/Desktop/agent-based-cti-argumentation-pipeline")


def pinned_modules():
    package = PIPELINE / "app/semantic_preparation"
    if not package.is_dir():
        pytest.skip("Installed Bottalico generator is unavailable")
    spec = importlib.util.spec_from_file_location("scientific_runner_tests", package / "runner.py")
    runner = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(runner)
    from thesis_agents.canonical.preparation import bytes_digest

    runner.verify_installation(bytes_digest((package / "installation-manifest.json").read_bytes()))
    return (
        runner.load("scientific_builder_tests", "src/semantic_assets/argumentation_graph.py"),
        runner.load("scientific_projection_tests", "tools/build_aln_projection.py"),
    )


def test_array_order_invariance_does_not_imply_semantic_renaming_invariance():
    builder, _ = pinned_modules()
    names = ["A", "B", "C", "D"]
    original = set(builder.ring_strategy_edges(names))
    assert set(builder.ring_strategy_edges(reversed(names))) == original
    rename = {"A": "A", "B": "C", "C": "B", "D": "D"}
    inverse = {v: k for k, v in rename.items()}
    renamed = {(inverse[a], inverse[b]) for a, b in builder.ring_strategy_edges(rename.values())}
    assert renamed != original


def test_projection_reuses_context_instead_of_inventing_different_action_profiles():
    _, projection = pinned_modules()
    metric = projection.MetricProfile(
        "metric", (3, 1), (("hasAttackVector", "AttackVectorNetwork"),)
    )
    first = projection.class_assertion("ActionA", "Solutions", ["Context"], metric)
    second = projection.class_assertion("ActionB", "Solutions", ["Context"], metric)
    a = projection.parse_axiom(first)
    b = projection.parse_axiom(second)
    # Exact asserted description equality suffices here; no inference is claimed.
    assert a.args[0] == b.args[0] and a.args[1] != b.args[1]
    assert "ObjectSomeValuesFrom(:hasAttackVector owl:Thing)" in first
    assert "ObjectAllValuesFrom(:hasAttackVector :AttackVectorNetwork)" in first
    assert "ObjectSomeValuesFrom(:hasAttackVector :AttackVectorNetwork)" not in first


def native_result(penalty, *, compatible=True):
    native = {
        "resourceIRI": "urn:asset",
        "score": max(0, 100 - penalty),
        "topPenalty": 0,
        "abductionPenalty": penalty if compatible else 0,
        "contractionPenalty": 0 if compatible else penalty,
        "hypothesis": "Hypothesis: Feature" if compatible else "",
        "giveUp": "" if compatible else "Give up: Conflict",
        "keep": "",
    }
    accepted = compatible and penalty == 0
    return {
        "valid": accepted,
        "status": "accepted"
        if accepted
        else "requires_prerequisites"
        if compatible
        else "rejected",
        "affinityScore": native["score"] / 100,
        "conflictPenalty": native["contractionPenalty"],
        "missingFeatures": [native["hypothesis"]] if compatible and penalty > 0 else [],
        "bonusFeatures": [],
        "bonusEvaluated": False,
        "explanation": "Explicit synthetic reasoning",
        "timestamp": "fixture",
        "reasoning": {
            "contract": "explain-affinity-v1",
            "ontologyKey": "tbox",
            "resourceIRI": "urn:asset",
            "requestIRI": "urn:action",
            "native": native,
        },
    }


@pytest.mark.parametrize(
    "penalty,compatible", [(0, True), (1, True), (125, True), (2, False), (125, False)]
)
def test_affinity_score_is_the_actual_v1_contract_not_a_bwaf_relation_weight(penalty, compatible):
    payload = native_result(penalty, compatible=compatible)
    result = SharedValidation.model_validate(payload)
    assert result.affinity_score == max(0, 100 - penalty) / 100
    assert result.reasoning.native.abduction_penalty == (penalty if compatible else 0)
    assert result.valid is (compatible and penalty == 0)
    assert result.bonus_evaluated is False


@pytest.mark.parametrize("score", [0, 50, 99])
def test_contradictory_native_score_is_technical_failure_even_with_consistent_normalization(score):
    payload = native_result(0)
    payload["reasoning"]["native"]["score"] = score
    payload["affinityScore"] = score / 100
    with pytest.raises(ValueError, match="score differs"):
        SharedValidation.model_validate(payload)


def test_symmetric_cycle_has_a_label_independent_tie_expectation():
    builder, _ = pinned_modules()
    names = ["A", "B", "C", "D"]
    edges = {("CVE", name) for name in names} | set(builder.ring_strategy_edges(names))
    rotation = dict(zip(names, names[1:] + names[:1], strict=True)) | {"CVE": "CVE"}
    # A graph automorphism, combined with identical profiles, requires tied scores
    # of a label-independent semantics; this does not compute any numeric ranking.
    assert {(rotation[a], rotation[b]) for a, b in edges} == edges


def test_reference_catalog_is_pinned_to_the_available_five_baselines():
    import hashlib

    catalog = json.loads(
        (Path(__file__).resolve().parents[1] / "config/scientific-graph-cases.v1.json").read_bytes()
    )
    ledger = Path("/Users/reucalion/Desktop/semantic-cti-ledger-argumentation")
    if not ledger.is_dir():
        pytest.skip("External baseline repository is unavailable")
    ontology = ledger / "chaincode-argumentation/onto/client_final_ontology.owl"
    assert hashlib.sha256(ontology.read_bytes()).hexdigest() == catalog["baseline_ontology_sha256"]
    assert len(catalog["cases"]) == 5
    for case in catalog["cases"]:
        graph = json.loads((ledger / case["original"]).read_bytes())
        assert len(graph["nodes"]) == case["nodes"] and len(graph["edges"]) == case["edges"]
        assert case["numeric_ranking_expected"] is None and case["live_status"] == "not_executed"
        edge_set = {(e["from"], e["to"]) for e in graph["edges"]}
        assert all((e["from"], e["to"]) in edge_set for e in case["expected_attack_edges"])
        for basename, digest in case["sha256"].items():
            assert (
                hashlib.sha256(
                    (ledger / Path(case["original"]).parent / basename).read_bytes()
                ).hexdigest()
                == digest
            )
