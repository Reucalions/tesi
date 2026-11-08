"""CAMEL Strategic role for contract-enforced recommendation publication."""

from camel.messages import BaseMessage
from camel.toolkits import FunctionTool

from thesis_agents.agents import strategic_selection
from thesis_agents.agents.contracts import AgentContract
from thesis_agents.orchestration.chat_agent import ArtifactChatAgent
from thesis_agents.strategic.agent import NativeStrategicPolicy

SELECTION_CONTRACT = AgentContract(
    role="StrategicAgent",
    task_id="strategic_native_selection",
    module=strategic_selection,
    inputs=(
        "runtime_evidence",
        "vulnerability_report",
        "candidate_strategies",
        "canonical_preparation",
        "native_strategic_ranking",
        "native_strategic_validation",
        "operational_profile",
    ),
    outputs=("native_strategic_recommendation",),
    task="StrategicAgent: read the validated native checkpoint and publish_native_recommendation. "
    "Select first effective acceptance per CVE; shared finalization remains pending.",
)


class SelectionPolicy(NativeStrategicPolicy):
    def observe(self, name, result):
        super().observe(name, result)
        if name == "get_context" and isinstance(result, dict):
            self.context_read = set(SELECTION_CONTRACT.inputs) <= result.get("artifacts", {}).keys()


def build_selection_agent(session, backend):
    return ArtifactChatAgent(
        system_message=BaseMessage.make_assistant_message(
            role_name="StrategicAgent", content=strategic_selection.PROMPT
        ),
        model=backend,
        tools=[FunctionTool(getattr(session, name)) for name in strategic_selection.TOOLS],
        tool_policy=SelectionPolicy(session),
        max_iteration=8,
        retry_attempts=1,
    )


def run_selection_agent(session, backend):
    build_selection_agent(session, backend).step(
        BaseMessage.make_user_message(role_name="Operator", content=SELECTION_CONTRACT.task)
    )
    return session.assert_complete()
