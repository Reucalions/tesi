"""Real CAMEL orchestration and tool dispatch, scripted inference ONLY for testing.

This verifies SDK integration without a network call. It is not an LLM evaluation.
"""

import ast
import json
import re
from collections import defaultdict

from camel.models.stub_model import StubModel
from camel.societies.workforce.workforce import WorkforceMode
from camel.types import ChatCompletion, ModelType

from thesis_agents.fixtures import fixture_candidates, fixture_evidence
from thesis_agents.orchestration.artifacts import ArtifactSession
from thesis_agents.orchestration.workforce import build_workforce, run_camel
from thesis_agents.schemas import CandidateStrategies, RuntimeEvidence, VulnerabilityReport


class ScriptedToolModel(StubModel):
    def __init__(self, session):
        super().__init__(ModelType.STUB)
        self.session = session
        self.steps = defaultdict(int)
        self.tool_calls = []
        self.received_contexts = {}

    @property
    def token_limit(self):
        # The SDK stub defaults to a tiny window that drops get_context's schemas.
        # Keep tool responses in memory so this test observes the actual handoff.
        return 128_000

    def _run(self, messages, response_format=None, tools=None):
        tool_names = {t["function"]["name"] for t in tools or []}
        if not tool_names:
            prompt = messages[-1]["content"]
            workers = dict(re.findall(r"<([^>]+)>:<([A-Za-z]+Agent):", prompt))
            roles = {role: id_ for id_, role in workers.items()}
            tasks = re.findall(r"Task ID: ([^\n]+)\nContent: ([A-Za-z]+Agent):", prompt)
            assert tasks and roles, f"Unexpected management request: {prompt[:160]}"
            payload = {
                "assignments": [
                    {"task_id": task_id, "assignee_id": roles[role], "dependencies": []}
                    for task_id, role in tasks
                ]
            }
            return self._completion(content=json.dumps(payload))

        if "publish_runtime_evidence" in tool_names:
            role = "telemetry"
            script = [
                ("get_context", {}),
                (
                    "publish_runtime_evidence",
                    {"payload": fixture_evidence(self.session).model_dump_json()},
                ),
            ]
        elif "publish_vulnerability_report" in tool_names:
            role = "vulnerability"
            script = [("get_context", {}), ("lookup_vulnerabilities", {})]
            if self.session._lookup is not None:
                script.append(
                    (
                        "publish_vulnerability_report",
                        {"payload": self.session._lookup.model_dump_json()},
                    )
                )
        elif "publish_candidate_strategies" in tool_names:
            role = "countermeasure"
            script = [
                ("get_context", {}),
                (
                    "publish_candidate_strategies",
                    {"payload": fixture_candidates(["CVE-2021-44228"]).model_dump_json()},
                ),
            ]
        else:
            role = "strategic"
            script = [
                ("get_context", {}),
                ("build_argumentation_graph", {}),
                ("rank_graph", {}),
                ("validate_countermeasure", {"strategy_id": "S_UPGRADE"}),
                (
                    "publish_final_decision",
                    {
                        "selected_strategy_id": "S_UPGRADE",
                        "explanation": "Scripted inference test; real CAMEL tool dispatch.",
                    },
                ),
                ("record_provenance", {}),
            ]
        step = self.steps[role]
        if step == 1:
            # Inspect what CAMEL actually delivered to the model after get_context,
            # rather than reading ArtifactSession directly in this assertion.
            context_messages = [message for message in messages if message.get("role") == "tool"]
            assert context_messages, "CAMEL must deliver the get_context tool response"
            context_message = context_messages[-1]
            content = context_message["content"]
            try:
                self.received_contexts[role] = json.loads(content)
            except json.JSONDecodeError:
                self.received_contexts[role] = ast.literal_eval(content)
        self.steps[role] += 1
        if step >= len(script):
            return self._completion(content=json.dumps({"content": "{}", "failed": False}))
        name, arguments = script[step]
        self.tool_calls.append(name)
        return self._completion(
            tool_calls=[
                {
                    "id": f"call-{role}-{step}",
                    "type": "function",
                    "function": {"name": name, "arguments": json.dumps(arguments)},
                }
            ]
        )

    async def _arun(self, messages, response_format=None, tools=None):
        return self._run(messages, response_format, tools)

    @staticmethod
    def _completion(content=None, tool_calls=None):
        message = {"role": "assistant", "content": content}
        if tool_calls:
            message["tool_calls"] = tool_calls
        return ChatCompletion.model_validate(
            {
                "id": "scripted-test",
                "model": "stub",
                "object": "chat.completion",
                "created": 0,
                "choices": [
                    {
                        "index": 0,
                        "finish_reason": "tool_calls" if tool_calls else "stop",
                        "message": message,
                    }
                ],
                "usage": {"prompt_tokens": 10, "completion_tokens": 10, "total_tokens": 20},
            }
        )


def test_real_workforce_dispatches_four_agents_and_publishes_artifacts(case, tmp_path):
    session = ArtifactSession(case, tmp_path, mode="camel", model="scripted-test-only")
    backend = ScriptedToolModel(session)
    result = run_camel(session, lambda: backend)
    assert result.selected_strategy_id == "S_UPGRADE"
    assert set(backend.steps) == {"telemetry", "vulnerability", "countermeasure", "strategic"}
    assert backend.tool_calls.count("lookup_vulnerabilities") == 1
    assert backend.tool_calls.count("rank_graph") == 1
    assert backend.tool_calls.count("record_provenance") == 1
    context = backend.received_contexts["strategic"]
    expected = {
        "runtime_evidence": (RuntimeEvidence, "TelemetryAgent"),
        "vulnerability_report": (VulnerabilityReport, "VulnerabilityAgent"),
        "candidate_strategies": (CandidateStrategies, "CountermeasureAgent"),
    }
    for name, (schema, producer) in expected.items():
        assert schema.model_validate(context["artifacts"][name]) == session.require(name, schema)
        assert context["artifact_producers"][name] == producer
    runtime = context["artifacts"]["runtime_evidence"]
    assert runtime == backend.received_contexts["vulnerability"]["artifacts"]["runtime_evidence"]
    assert runtime == backend.received_contexts["countermeasure"]["artifacts"]["runtime_evidence"]
    assert (
        context["artifacts"]["vulnerability_report"]
        == (backend.received_contexts["countermeasure"]["artifacts"]["vulnerability_report"])
    )
    assert result.evidence_ids == [s["evidence_id"] for s in runtime["software"]]


def test_default_pipeline_has_explicit_producer_dependencies(case, tmp_path):
    session = ArtifactSession(case, tmp_path, mode="camel", model="scripted-test-only")
    workforce = build_workforce(session, lambda: ScriptedToolModel(session))
    assert workforce.mode == WorkforceMode.PIPELINE
    expected = {
        "telemetry": [],
        "vulnerability": ["telemetry"],
        "countermeasure": ["telemetry", "vulnerability"],
        "strategic": ["telemetry", "vulnerability", "countermeasure"],
    }
    # Check both the task objects and CAMEL's actual scheduling dependency map.
    assert {t.id: [d.id for d in t.dependencies] for t in workforce._pending_tasks} == expected
    assert workforce._task_dependencies == expected
