"""Agente CAMEL del checkpoint: get_context -> prepare_argumentation -> pubblicazione."""

from camel.messages import BaseMessage
from camel.terminators import ResponseTerminator
from camel.toolkits import FunctionTool

from thesis_agents.agents import semantic_preparation
from thesis_agents.agents.contracts import AgentContract
from thesis_agents.orchestration.chat_agent import ArtifactChatAgent

PREPARATION_CONTRACT = AgentContract(
    role="SemanticPreparationAgent",
    task_id="semantic_preparation",
    module=semantic_preparation,
    inputs=("runtime_evidence", "vulnerability_report", "candidate_strategies"),
    outputs=("canonical_preparation",),
    task=(
        "SemanticPreparationAgent: read source artifacts, execute preparation "
        "and publish its checkpoint."
    ),
)


class PreparationPolicy(ResponseTerminator):
    def __init__(self, session):
        super().__init__()
        self.session = session
        self.reset()

    def reset(self):
        self.context_read = False

    def clone(self):
        return type(self)(self.session)

    def next_tool(self):
        if not self.context_read:
            return "get_context"
        return "prepare_argumentation" if self.session._artifact is None else None

    def observe(self, name, result):
        if name == "get_context" and isinstance(result, dict):
            self.context_read = (
                set(PREPARATION_CONTRACT.inputs) <= result.get("artifacts", {}).keys()
            )

    def instruction(self):
        return (
            f"Call {self.next_tool()} with {{}}." if self.next_tool() else "Checkpoint published."
        )

    def is_terminated(self, messages):
        return self.next_tool() is None, "Canonical checkpoint published"


def build_preparation_agent(session, backend):
    return ArtifactChatAgent(
        system_message=BaseMessage.make_assistant_message(
            role_name=PREPARATION_CONTRACT.role, content=semantic_preparation.PROMPT
        ),
        model=backend,
        tools=[FunctionTool(getattr(session, name)) for name in semantic_preparation.TOOLS],
        tool_policy=PreparationPolicy(session),
        max_iteration=12,
        retry_attempts=1,
    )


def run_preparation_agent(session, backend):
    agent = build_preparation_agent(session, backend)
    agent.step(
        BaseMessage.make_user_message(role_name="Operator", content=PREPARATION_CONTRACT.task)
    )
    return session.assert_complete()
