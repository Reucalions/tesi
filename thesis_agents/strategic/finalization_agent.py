"""CAMEL Strategic phase for shared recommendation and provenance registration."""

from functools import wraps

from camel.messages import BaseMessage
from camel.toolkits import FunctionTool

from thesis_agents.agents import strategic_finalization
from thesis_agents.agents.contracts import AgentContract
from thesis_agents.orchestration.chat_agent import ArtifactChatAgent
from thesis_agents.strategic.agent import NativeStrategicPolicy

FINALIZATION_CONTRACT = AgentContract(
    role="StrategicAgent",
    task_id="strategic_native_finalization",
    module=strategic_finalization,
    inputs=(
        "runtime_evidence",
        "vulnerability_report",
        "candidate_strategies",
        "canonical_preparation",
        "native_strategic_ranking",
        "native_strategic_validation",
        "validation_profile",
        "native_strategic_recommendation",
    ),
    outputs=("native_strategic_finalization",),
    task="StrategicAgent: read verified selection and producer artifacts; register each fixed CVE "
    "recommendation, read its commit/provenance back, then publish_native_finalization.",
)


class FinalizationPolicy(NativeStrategicPolicy):
    def observe(self, name, result):
        super().observe(name, result)
        if name == "get_context" and isinstance(result, dict):
            self.context_read = (
                set(FINALIZATION_CONTRACT.inputs) <= result.get("artifacts", {}).keys()
            )


def _receipt_view(response):
    # The session has validated and archived the full wire response. The model
    # needs the verified receipt/digests, not escaped copies of the same documents.
    record = response["record"]
    return {
        "view": "verified-finalization-receipt-v1",
        "record": {
            key: record[key]
            for key in ("finalization_id", "transaction_id", "document_sha256", "provenance_sha256")
        },
        **{
            key: response[key]
            for key in (
                "commit",
                "ledger_readback_verified",
                "verification_scope",
                "deployment_verified",
                "action_execution",
            )
        },
    }


def _finalization_tool(session, name):
    method = getattr(session, name)
    if name == "get_context":
        return method  # Keep every original producer artifact available to the agent.

    @wraps(method)
    def operation() -> dict:
        response = method()  # No summary is returned before the original checks succeed.
        if name == "publish_native_finalization":
            return {
                "view": "native-finalization-publication-v1",
                **{
                    key: response[key]
                    for key in (
                        "run_id",
                        "asset_id",
                        "backend_kind",
                        "status",
                        "shared_finalization",
                        "verification_scope",
                        "deployment_verified",
                        "action_execution",
                    )
                },
                "results": [_receipt_view(row) for row in response["results"]],
            }
        return {**_receipt_view(response), "next_operation": session.next_operation()}

    return operation


def build_finalization_agent(session, backend):
    return ArtifactChatAgent(
        system_message=BaseMessage.make_assistant_message(
            role_name="StrategicAgent", content=strategic_finalization.PROMPT
        ),
        model=backend,
        tools=[
            FunctionTool(_finalization_tool(session, name)) for name in strategic_finalization.TOOLS
        ],
        tool_policy=FinalizationPolicy(session),
        max_iteration=8 + 2 * len(session.recommendation.results),
        retry_attempts=1,
    )


def run_finalization_agent(session, backend):
    build_finalization_agent(session, backend).step(
        BaseMessage.make_user_message(role_name="Operator", content=FINALIZATION_CONTRACT.task)
    )
    return session.assert_complete()
