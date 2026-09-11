"""Regressione del falso successo osservato nella prima prova Ollama."""

import pytest
from camel.societies.workforce.single_agent_worker import PROCESS_TASK_PROMPT
from camel.societies.workforce.utils import TaskResult

from thesis_agents.fixtures import fixture_evidence
from thesis_agents.orchestration.task_results import ArtifactTaskHandler


def test_claimed_success_without_publication_is_rejected(session):
    handler = ArtifactTaskHandler(session, ("runtime_evidence",))
    result = handler.parse_structured_response(
        '{"content": "I published the runtime evidence", "failed": false}', TaskResult
    )
    assert result.failed
    assert "runtime_evidence" in result.content
    assert not (session.output_dir / "runtime_evidence.json").exists()


def test_actual_publication_allows_success(session):
    session.publish_runtime_evidence(fixture_evidence(session).model_dump_json())
    handler = ArtifactTaskHandler(session, ("runtime_evidence",))
    result = handler.parse_structured_response(
        '{"content": "Published", "failed": false}', TaskResult
    )
    assert not result.failed


def test_model_failure_is_not_masked_by_existing_artifact(session):
    session.publish_runtime_evidence(fixture_evidence(session).model_dump_json())
    handler = ArtifactTaskHandler(session, ("runtime_evidence",))
    result = handler.parse_structured_response(
        '{"content": "Cannot complete task", "failed": true}', TaskResult
    )
    assert result.failed


def test_prompt_adapter_preserves_task_and_dependency_context(session):
    handler = ArtifactTaskHandler(session, ("runtime_evidence",))
    base = PROCESS_TASK_PROMPT.format(
        content="Task content sentinel",
        parent_task_content="Parent sentinel",
        dependency_tasks_info="Dependency sentinel",
        additional_info="Additional info sentinel",
    )
    prompt = handler.generate_structured_prompt(base, TaskResult)
    for text in (
        "Task content sentinel",
        "Parent sentinel",
        "Dependency sentinel",
        "Additional info sentinel",
    ):
        assert text in prompt
    assert "The calculation result is 4" not in prompt


def test_changed_sdk_prompt_requires_review(session):
    handler = ArtifactTaskHandler(session, ("runtime_evidence",))
    with pytest.raises(RuntimeError, match="SDK compatibility"):
        handler.generate_structured_prompt("Unexpected SDK template", TaskResult)
