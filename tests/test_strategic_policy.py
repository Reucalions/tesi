"""Regressioni SDK: fasi, falso successo, errori, cloni e input distinti."""

import asyncio
import json
from importlib.resources import files

import pytest
from camel.agents._types import ToolCallRequest
from test_camel_integration import ScriptedToolModel

from thesis_agents.fixtures import fixture_candidates, fixture_evidence
from thesis_agents.orchestration.artifacts import ArtifactSession
from thesis_agents.orchestration.workforce import build_workforce
from thesis_agents.schemas import StaticTelemetry


def prepare(case, tmp_path):
    session = ArtifactSession(case, tmp_path, mode="camel", model="scripted-test-only")
    session.publish_runtime_evidence(fixture_evidence(session).model_dump_json())
    report = session.lookup_vulnerabilities()
    session.publish_vulnerability_report(json.dumps(report))
    session.publish_candidate_strategies(
        fixture_candidates([v["cve_id"] for v in report["vulnerabilities"]]).model_dump_json()
    )
    return session


class PhaseModel(ScriptedToolModel):
    def __init__(self, session):
        super().__init__(session)
        self.offered = []
        self.premature = False
        self.rejected = False

    def _run(self, messages, response_format=None, tools=None):
        names = {t["function"]["name"] for t in tools or []}
        self.offered.append(names.copy())
        if not names:
            return self._completion(content='{"content":"Published", "failed":false}')
        assert len(names) == 1
        name = names.pop()
        args = {}
        if name == "validate_countermeasure":
            ranking = self.session.get_context()["artifacts"]["ranking"]["ranking"]
            attempted = self.session.get_context()["artifacts"].get("semantic_validation", {})
            index = len(attempted.get("validations", []))
            args = {"strategy_id": ranking[index]["strategy_id"]}
        elif name == "publish_final_decision":
            if not self.premature:
                self.premature = True
                return self._completion(content='{"name":"publish_final_decision","arguments":{}}')
            vals = self.session.get_context()["artifacts"].get("semantic_validation", {})
            selected = next(
                (v["strategy_id"] for v in vals.get("validations", []) if v["valid"]), None
            )
            if not self.rejected:
                self.rejected = True
                selected = "S_INVENTED"  # Il rifiuto deve mantenere la stessa fase.
            args = {"selected_strategy_id": selected, "explanation": "Scripted phase test"}
        return self._completion(
            tool_calls=[
                {
                    "id": f"phase-{len(self.offered)}",
                    "type": "function",
                    "function": {"name": name, "arguments": json.dumps(args)},
                }
            ]
        )


@pytest.mark.parametrize("async_call", [False, True])
@pytest.mark.parametrize(
    "scenario", ["demo_01_nominal", "demo_03_all_actions_prohibited", "demo_04_unsupported_lookup"]
)
def test_phases_survive_text_and_rejected_publication(tmp_path, scenario, async_call):
    case = StaticTelemetry.model_validate_json(
        files("thesis_agents").joinpath(f"data/{scenario}.json").read_text()
    )
    session = prepare(case, tmp_path)
    before = {p.name: p.read_bytes() for p in tmp_path.glob("*.json")}
    model = PhaseModel(session)
    agent = build_workforce(session, lambda: model)._children[3].worker.clone().clone()
    response = (
        asyncio.run(agent.astep("Complete strategic publications"))
        if async_call
        else agent.step("Complete strategic publications")
    )
    assert response.msgs
    session.assert_complete()
    assert model.offered[:3] == [{"get_context"}, {"build_argumentation_graph"}, {"rank_graph"}]
    assert model.offered[-2:] == [{"record_provenance"}, set()]
    assert model.offered.count({"publish_final_decision"}) == 3
    expected_validations = {
        "demo_01_nominal": 1,
        "demo_03_all_actions_prohibited": 4,
        "demo_04_unsupported_lookup": 0,
    }
    assert model.offered.count({"validate_countermeasure"}) == expected_validations[scenario]
    for name, value in before.items():
        assert (tmp_path / name).read_bytes() == value
    # Ogni clone rilegge il contesto anche se la sessione contiene già la decisione.
    clone = agent.clone()
    assert clone.tool_policy.next_tool() == "get_context"
    assert agent.tool_policy.next_tool() is None


@pytest.mark.parametrize("async_call", [False, True])
def test_unadvertised_tool_is_rejected_before_backend(case, tmp_path, async_call):
    session = prepare(case, tmp_path)
    model = PhaseModel(session)
    agent = build_workforce(session, lambda: model)._children[3].worker.clone()
    request = ToolCallRequest(
        tool_name="build_argumentation_graph", args={}, tool_call_id="out-of-phase"
    )
    result = (
        asyncio.run(agent._aexecute_tool(request)) if async_call else agent._execute_tool(request)
    )
    assert "Tool execution failed" in result.result
    assert not (tmp_path / "argumentation_graph.json").exists()
    assert agent.tool_policy.next_tool() == "get_context"


def test_repeated_text_cannot_create_publications(case, tmp_path):
    class TextOnlyModel(ScriptedToolModel):
        calls = 0

        def _run(self, messages, response_format=None, tools=None):
            self.calls += 1
            return self._completion(content='{"content":"Everything is saved", "failed":false}')

    session = prepare(case, tmp_path)
    model = TextOnlyModel(session)
    worker = build_workforce(session, lambda: model)._children[3]
    from camel.tasks import Task
    from camel.tasks.task import TaskState

    task = Task(id="strategic", content="Complete strategic publications")
    assert asyncio.run(worker._process_task(task, [])) == TaskState.FAILED
    assert model.calls == 2
    assert "Publication contract failed" in task.result
    assert not (tmp_path / "final_decision.json").exists()
