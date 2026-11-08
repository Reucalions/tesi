"""Il ruolo Strategic CAMEL invoca singolarmente i tool del profilo nativo."""

import json

from camel.messages import BaseMessage
from camel.terminators import ResponseTerminator
from camel.toolkits import FunctionTool

from thesis_agents.agents import strategic_native
from thesis_agents.agents.contracts import AgentContract
from thesis_agents.orchestration.chat_agent import ArtifactChatAgent

NATIVE_STRATEGIC_CONTRACT = AgentContract(
    role="StrategicAgent",
    task_id="strategic_native_ranking",
    module=strategic_native,
    inputs=(
        "runtime_evidence",
        "vulnerability_report",
        "candidate_strategies",
        "canonical_preparation",
    ),
    outputs=("native_strategic_ranking",),
    task=(
        "StrategicAgent: read MAS inputs and canonical preparation, rank each CVE through "
        "shared MCP, read decision and provenance back, then publish_native_ranking. "
        "Semantic selection remains pending."
    ),
)


class NativeStrategicPolicy(ResponseTerminator):
    def __init__(self, session):
        super().__init__()
        self.session = session
        self.reset()

    def reset(self):
        self.context_read = False
        self.premature_responses = 0

    def clone(self):
        return type(self)(self.session)

    def next_tool(self):
        if self.session._failed:
            return None
        if not self.context_read:
            return "get_context"
        operation = self.session.next_operation()
        return operation["tool"] if operation else None

    def observe(self, name, result):
        if name == "get_context" and isinstance(result, dict):
            self.context_read = (
                set(NATIVE_STRATEGIC_CONTRACT.inputs) <= result.get("artifacts", {}).keys()
            )
        if isinstance(result, dict):
            self.premature_responses = 0

    def instruction(self):
        tool = self.next_tool()
        if tool is None:
            return "Native ranking checkpoint published or task failed. Do not invent a decision."
        operation = self.session.next_operation() if tool != "get_context" else {}
        arguments = {key: value for key, value in operation.items() if key != "tool"}
        return f"Call {tool} with {json.dumps(arguments)} through a real tool call."

    def is_terminated(self, messages):
        if self.next_tool() is None:
            return True, "Native Strategic checkpoint complete or failed"
        self.premature_responses += 1
        return self.premature_responses >= 2, "Required native ranking publications still missing"


def build_native_strategic_agent(session, backend):
    return ArtifactChatAgent(
        system_message=BaseMessage.make_assistant_message(
            role_name=NATIVE_STRATEGIC_CONTRACT.role, content=strategic_native.PROMPT
        ),
        model=backend,
        tools=[FunctionTool(getattr(session, name)) for name in strategic_native.TOOLS],
        tool_policy=NativeStrategicPolicy(session),
        max_iteration=6 + 3 * len(session.preparation.graphs),
        retry_attempts=1,
    )


def run_native_strategic_agent(session, backend):
    agent = build_native_strategic_agent(session, backend)
    agent.step(
        BaseMessage.make_user_message(role_name="Operator", content=NATIVE_STRATEGIC_CONTRACT.task)
    )
    return session.assert_complete()
