"""Regressioni del blocco Ollama: testo non eseguito, fasi, errori e cloni."""

import asyncio
import json

import pytest
import test_package_verification
from camel.agents._types import ToolCallRequest
from test_camel_integration import ScriptedToolModel

from thesis_agents.orchestration.workforce import build_workforce

apache_files = test_package_verification.apache_files
request_and_response = test_package_verification.request_and_response
sample = test_package_verification.sample
v2_sample = test_package_verification.v2_sample
package_sample = test_package_verification.package_sample
resolved_package = test_package_verification.resolved_package
prepared = test_package_verification.prepared


class CountermeasurePhaseModel(ScriptedToolModel):
    def __init__(self, session):
        super().__init__(session)
        self.offered = []
        self.publications = 0

    def _run(self, messages, response_format=None, tools=None):
        names = {t["function"]["name"] for t in tools or []}
        self.offered.append(names)
        if not names:
            return self._completion(content='{"content":"Published", "failed":false}')
        assert len(names) == 1
        name = next(iter(names))
        arguments = {}
        if name == "publish_candidate_strategies":
            self.publications += 1
            if self.publications == 1:
                return self._completion(
                    content='{"name":"publish_candidate_strategies","arguments":{}}'
                )
            arguments = {"payload": {"strategies": []}}
            if self.publications > 2:
                arguments["payload"]["verification_requests"] = [
                    r.model_dump(mode="json")
                    for r in self.session._package_verification_context.verification_requests
                ]
        return self._completion(
            tool_calls=[
                {
                    "id": f"countermeasure-phase-{len(self.offered)}",
                    "type": "function",
                    "function": {"name": name, "arguments": json.dumps(arguments)},
                }
            ]
        )


@pytest.mark.parametrize("async_call", [False, True])
def test_countermeasure_phases_recover_from_text_and_rejected_payload(prepared, async_call):
    before = {p.name: p.read_bytes() for p in prepared.output_dir.glob("*.json")}
    model = CountermeasurePhaseModel(prepared)
    agent = build_workforce(prepared, lambda: model)._children[2].worker.clone().clone()
    if async_call:
        asyncio.run(agent.astep("Publish package verification requests"))
    else:
        agent.step("Publish package verification requests")
    payload = prepared.get_context()["artifacts"]["candidate_strategies"]
    assert payload["strategies"] == [] and len(payload["verification_requests"]) == 4
    assert model.offered[:3] == [{"get_context"}, {"prepare_package_verification"}, {"get_context"}]
    assert model.offered.count({"publish_candidate_strategies"}) == 3
    assert agent.clone().tool_policy.next_tool() == "get_context"
    assert agent.tool_policy.next_tool() is None
    assert all((prepared.output_dir / name).read_bytes() == data for name, data in before.items())


@pytest.mark.parametrize("async_call", [False, True])
def test_countermeasure_rejects_out_of_phase_publication(prepared, async_call):
    model = CountermeasurePhaseModel(prepared)
    agent = build_workforce(prepared, lambda: model)._children[2].worker.clone()
    request = ToolCallRequest(
        tool_name="publish_candidate_strategies", args={}, tool_call_id="early"
    )
    result = (
        asyncio.run(agent._aexecute_tool(request)) if async_call else agent._execute_tool(request)
    )
    assert "Tool execution failed" in result.result
    assert not (prepared.output_dir / "candidate_strategies.json").exists()
    assert agent.tool_policy.next_tool() == "get_context"


@pytest.mark.parametrize("async_call", [False, True])
def test_text_only_countermeasure_does_not_create_output(prepared, async_call):
    class TextModel(CountermeasurePhaseModel):
        def _run(self, messages, response_format=None, tools=None):
            return self._completion(content='{"content":"Everything published", "failed":false}')

    model = TextModel(prepared)
    agent = build_workforce(prepared, lambda: model)._children[2].worker.clone()
    if async_call:
        asyncio.run(agent.astep("Publish checks"))
    else:
        agent.step("Publish checks")
    assert not (prepared.output_dir / "candidate_strategies.json").exists()
    assert agent.tool_policy.next_tool() == "get_context"
