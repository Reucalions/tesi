"""Il budget deve bloccare prima del provider, senza perdere evidenze in memoria."""

import asyncio
from copy import deepcopy
from unittest.mock import AsyncMock, Mock

import pytest
from camel.agents import ChatAgent
from camel.models.openai_compatible_model import OpenAICompatibleModel
from pydantic import BaseModel, Field

from thesis_agents.config import ModelSettings
from thesis_agents.orchestration.bounded_model import BoundedCompatibleModel
from thesis_agents.orchestration.chat_agent import ArtifactChatAgent


def backend():
    return BoundedCompatibleModel(
        model_type="local-context-test",
        api_key="local",
        url="http://127.0.0.1:11434/v1",
        model_config_dict={"max_tokens": 256},
        context_tokens=4096,
    )


@pytest.mark.parametrize("async_call", [False, True])
@pytest.mark.parametrize("large_part", ["messages", "tools", "schema"])
def test_oversized_request_never_reaches_provider(monkeypatch, async_call, large_part):
    model = backend()
    messages = [{"role": "user", "content": "Read the published evidence."}]
    tools = [{"type": "function", "function": {"name": "get_context", "description": "small"}}]
    response_format = None
    big = "observation " * 5000
    if large_part == "messages":
        messages.append({"role": "tool", "content": big, "tool_call_id": "evidence"})
    elif large_part == "tools":
        tools[0]["function"]["description"] = big
    else:

        class LargeResponse(BaseModel):
            evidence: str = Field(description=big)

        response_format = LargeResponse
    original = deepcopy((messages, tools))
    call = AsyncMock() if async_call else Mock()
    monkeypatch.setattr(OpenAICompatibleModel, "_arun" if async_call else "_run", call)
    with pytest.raises(RuntimeError, match="request not sent"):
        if async_call:
            asyncio.run(model._arun(messages, response_format, tools))
        else:
            model._run(messages, response_format, tools)
    call.assert_not_called()
    assert (messages, tools) == original


@pytest.mark.parametrize("async_call", [False, True])
def test_within_budget_reaches_original_backend_unchanged(monkeypatch, async_call):
    model = backend()
    messages = [{"role": "user", "content": "Preserve null and the empty finding list."}]
    tools = [{"type": "function", "function": {"name": "get_context", "parameters": {}}}]
    call = AsyncMock(return_value="response") if async_call else Mock(return_value="response")
    monkeypatch.setattr(OpenAICompatibleModel, "_arun" if async_call else "_run", call)
    result = (
        asyncio.run(model._arun(messages, tools=tools))
        if async_call
        else model._run(messages, tools=tools)
    )
    assert result == "response"
    call.assert_called_once_with(messages, None, tools)


def test_agent_clone_preserves_explicit_backend_and_context_limit():
    agent = ChatAgent("Preserve the authoritative artifacts", model=backend())
    clone = agent.clone()
    assert agent.token_limit == clone.token_limit == 4096
    assert isinstance(clone.model_backend.models[0], BoundedCompatibleModel)


def test_worker_clones_keep_full_memory_without_summarizing(monkeypatch):
    agent = ArtifactChatAgent("Preserve evidence", model=backend(), retry_attempts=1)
    agent = agent.clone().clone()
    assert agent.summarize_threshold is None
    assert agent.token_limit == 4096
    messages = [{"role": "tool", "content": "authoritative evidence", "tool_call_id": "E1"}]
    # Oltre metà contesto l'SDK attiverebbe un riassunto; oltre il limite deve
    # ancora arrivare la richiesta integrale al guard del backend, che la rifiuta.
    for count in (3000, 5000):
        monkeypatch.setattr(agent.memory, "get_context", lambda count=count: (messages, count))
        summarizer = Mock(side_effect=AssertionError("Evidence must not be summarized"))
        monkeypatch.setattr(agent, "summarize", summarizer)
        monkeypatch.setattr(agent, "asummarize", summarizer)
        assert agent._get_context_with_summarization() == (messages, count)
        assert asyncio.run(agent._get_context_with_summarization_async()) == (messages, count)
        summarizer.assert_not_called()


def test_clone_with_memory_preserves_records_without_sharing_store():
    from camel.messages import BaseMessage

    agent = ArtifactChatAgent("Preserve evidence", model=backend())
    agent.record_message(BaseMessage.make_user_message("user", "evidence E1"))
    clone = agent.clone(with_memory=True)
    original = agent.memory.get_context()[0]
    assert clone.memory.get_context()[0] == original
    clone.reset()
    assert agent.memory.get_context()[0] == original
    assert len(clone.memory.get_context()[0]) < len(original)


@pytest.mark.parametrize("context", ["0", "-1", "invalid", "2048"])
def test_invalid_context_configuration_is_rejected(monkeypatch, context):
    for key, value in {
        "LLM_MODEL": "local-test",
        "LLM_API_KEY": "local",
        "LLM_BASE_URL": "http://localhost:11434/v1",
        "LLM_MAX_TOKENS": "2048",
        "LLM_CONTEXT_TOKENS": context,
    }.items():
        monkeypatch.setenv(key, value)
    with pytest.raises(ValueError, match="LLM_CONTEXT_TOKENS"):
        ModelSettings.from_env()


def test_env_configuration_constructs_bounded_backend(monkeypatch):
    for key, value in {
        "LLM_MODEL": "local-test",
        "LLM_API_KEY": "local",
        "LLM_BASE_URL": "http://localhost:11434/v1",
        "LLM_MAX_TOKENS": "2048",
        "LLM_CONTEXT_TOKENS": "16384",
    }.items():
        monkeypatch.setenv(key, value)
    model = ModelSettings.from_env().create_backend()
    assert isinstance(model, BoundedCompatibleModel)
    assert model.token_limit == 16384
    assert model.model_config_dict["max_tokens"] == 2048
