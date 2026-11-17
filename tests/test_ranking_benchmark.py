"""Verify numerical comparison and native-proof auditing, without live services."""

import copy
import json

import pytest

from evaluation.run_ranking_benchmark import audit, compare, ranking, topology, unwrap, winners


def test_score_comparison_is_symmetric_and_independent_of_order():
    first = {"a": 0.1, "b": 0.5}
    second = {"b": 0.5, "a": 0.2}
    assert not compare(first, second)["scores_equal"]
    assert not compare(second, first)["scores_equal"]
    assert compare(first, dict(reversed(list(first.items()))))["scores_exact"]
    assert first == {"a": 0.1, "b": 0.5}


@pytest.mark.parametrize(
    "rows",
    [
        [],
        [{"name": "a"}],
        [{"name": "a", "score": None}],
        [{"name": "a", "score": float("nan")}],
        [{"name": "a", "score": True}],
        [{"name": "a", "score": 1}, {"name": "a", "score": 2}],
    ],
)
def test_missing_or_invalid_ranking_is_not_a_determinism_proof(rows):
    with pytest.raises((KeyError, ValueError)):
        ranking(rows)
    assert not compare({}, {})["scores_equal"]


def test_winners_compare_tied_sets_instead_of_serialization_order():
    assert winners({"a": 1, "b": 1 - 0.5e-6, "c": 0.9}) == ["a", "b"]
    result = compare({"a": 1, "b": 1}, {"a": 1 - 0.5e-6, "b": 1})
    assert result["winner_equal"] and result["scores_equal"]
    assert not compare({"a": 1}, {"b": 1})["comparable"]


def example():
    graph = {
        "nodes": [
            {"id": "v", "type": "vulnerability"},
            {"id": "a", "type": "strategy"},
            {"id": "b", "type": "strategy"},
        ],
        "edges": [{"from": "v", "to": "a"}, {"from": "v", "to": "b"}],
    }
    native = {
        "nodes": [
            {"data": {"id": i, "label": label}} for i, label in [(9, "v"), (2, "a"), (5, "b")]
        ],
        "edges": [
            {"data": {"source": 9, "target": 2, "label": 0.5}},
            {"data": {"source": 9, "target": 5, "label": -0.2}},
        ],
    }
    rows = [
        {
            "name": "a",
            "score": 0.8,
            "explanation": {"against": [{"path": [9, 2], "strengthProduct": 0.5}]},
        },
        {"name": "b", "score": 0.6},
    ]
    return graph, rows, native, {"expected_attack_edges": [{"from": "v", "to": "b"}]}


def test_positive_against_is_reported_separately_from_valid_path_product():
    result = audit(*example())
    assert result["candidate_and_topology_complete"]
    assert result["path_products_valid"]
    assert result["sign_interpretation_disagreements"] == 1
    assert result["candidates_without_paths"] == ["b"]
    assert result["expected_clashes_negative"]


def test_wrong_direction_or_product_is_detected_without_guessing_node_offset():
    graph, rows, native, case = example()
    bad = copy.deepcopy(rows)
    bad[0]["explanation"]["against"][0]["path"] = [2, 9]
    assert not audit(graph, bad, native, case)["path_products_valid"]
    bad = copy.deepcopy(rows)
    bad[0]["explanation"]["against"][0]["strengthProduct"] = 0.7
    assert not audit(graph, bad, native, case)["path_products_valid"]


def test_permutation_requires_exact_node_types_and_directed_edges():
    graph = example()[0]
    reordered = {k: list(reversed(v)) for k, v in graph.items()}
    assert topology(graph) == topology(reordered)
    changed = copy.deepcopy(reordered)
    changed["edges"][0] = {"from": "b", "to": "v"}
    assert topology(graph) != topology(changed)
    duplicate = copy.deepcopy(graph)
    duplicate["nodes"].append(duplicate["nodes"][0])
    with pytest.raises(ValueError):
        topology(duplicate)


def test_nested_backend_error_is_not_a_successful_empty_read():
    def wire(value):
        return {"content": [{"type": "text", "text": json.dumps({"ok": True, "payload": value})}]}

    assert unwrap(wire({"response": {"success": '[{"name":"a","score":1}]'}})) == [
        {"name": "a", "score": 1}
    ]
    with pytest.raises(ValueError):
        unwrap(wire({"response": {"error": "NOT_FOUND"}}))
