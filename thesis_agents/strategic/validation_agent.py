"""Strategic CAMEL sul checkpoint di ranking, con tool di validazione distinti."""

from camel.messages import BaseMessage
from camel.toolkits import FunctionTool

from thesis_agents.agents import strategic_validation
from thesis_agents.agents.contracts import AgentContract
from thesis_agents.orchestration.chat_agent import ArtifactChatAgent
from thesis_agents.strategic.agent import NativeStrategicPolicy

VALIDATION_CONTRACT = AgentContract(
    role="StrategicAgent",
    task_id="strategic_native_validation",
    module=strategic_validation,
    inputs=(
        "runtime_evidence",
        "vulnerability_report",
        "candidate_strategies",
        "canonical_preparation",
        "native_strategic_ranking",
        "operational_profile",
    ),
    outputs=("native_strategic_validation",),
    task="StrategicAgent: read native ranking and operator policy, validate candidates in order, "
    "then publish_native_validation. Recommendation remains pending.",
)


class ValidationPolicy(NativeStrategicPolicy):
    def observe(self, name, result):
        super().observe(name, result)
        if name == "get_context" and isinstance(result, dict):
            self.context_read = (
                set(VALIDATION_CONTRACT.inputs) <= result.get("artifacts", {}).keys()
            )


def build_validation_agent(session, backend):
    return ArtifactChatAgent(
        system_message=BaseMessage.make_assistant_message(
            role_name="StrategicAgent", content=strategic_validation.PROMPT
        ),
        model=backend,
        tools=[FunctionTool(getattr(session, name)) for name in strategic_validation.TOOLS],
        tool_policy=ValidationPolicy(session),
        max_iteration=6 + len(session._requests),
        retry_attempts=1,
    )


def run_validation_agent(session, backend):
    agent = build_validation_agent(session, backend)
    agent.step(
        BaseMessage.make_user_message(role_name="Operator", content=VALIDATION_CONTRACT.task)
    )
    return session.assert_complete()
