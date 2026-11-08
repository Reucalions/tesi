"""Executable native DAG: dependencies, publication boundaries and failure blocking."""

import pytest

from thesis_agents.orchestration.native_dag import NativeArtifactDAG, native_dependencies


def test_native_dag_retains_each_producer_and_all_join_dependencies():
    deps = native_dependencies()
    assert deps["telemetry"] == ()
    assert deps["countermeasure"] == ("telemetry", "vulnerability")
    assert deps["semantic_preparation"] == ("telemetry", "vulnerability", "countermeasure")
    assert deps["strategic_native_selection"] == (
        "telemetry",
        "vulnerability",
        "countermeasure",
        "semantic_preparation",
        "strategic_native_ranking",
        "strategic_native_validation",
    )


def test_out_of_order_invocation_never_runs_agent_and_blocks_descendants(tmp_path):
    dag = NativeArtifactDAG(tmp_path, run_id="run-test", workflow="pipeline")
    calls = []
    with pytest.raises(ValueError, match="prerequisite"):
        dag.execute("strategic_native_ranking", lambda: calls.append(1), lambda: None)
    assert not calls
    assert dag.state["nodes"]["strategic_native_ranking"]["status"] == "failed"
    assert dag.state["nodes"]["strategic_native_validation"]["status"] == "blocked"
    assert dag.state["nodes"]["strategic_native_selection"]["status"] == "blocked"


def test_successful_prose_without_valid_publication_does_not_release_descendants(tmp_path):
    dag = NativeArtifactDAG(tmp_path, run_id="run-test", workflow="pipeline")
    for task in ("telemetry", "vulnerability", "countermeasure"):
        dag.complete_source(task, lambda: None)

    def unpublished():
        raise ValueError("canonical_preparation unpublished")

    with pytest.raises(ValueError, match="unpublished"):
        dag.execute("semantic_preparation", lambda: "Everything is done", unpublished)
    assert dag.state["nodes"]["semantic_preparation"]["status"] == "failed"
    assert dag.state["nodes"]["strategic_native_selection"]["status"] == "blocked"


def test_changed_prerequisite_is_rechecked_before_downstream_inference(tmp_path):
    dag = NativeArtifactDAG(tmp_path, run_id="run-test", workflow="pipeline")
    valid = [True]

    def check():
        if not valid[0]:
            raise ValueError("source changed")

    dag.complete_source("telemetry", check)
    dag.complete_source("vulnerability", lambda: None)
    dag.complete_source("countermeasure", lambda: None)
    valid[0] = False
    calls = []
    with pytest.raises(ValueError, match="source changed"):
        dag.execute("semantic_preparation", lambda: calls.append(1), lambda: None)
    assert not calls
