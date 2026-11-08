"""Contratti dei ruoli, condivisi da scheduler, handler e policy dei tool.

Le dipendenze dei task derivano dagli artefatti richiesti e dai loro produttori.
Prompt e tool restano nei moduli dei singoli agenti; qui non si esegue il dominio.
"""

from dataclasses import dataclass
from types import MappingProxyType, ModuleType

from . import countermeasure, strategic, telemetry, vulnerability


@dataclass(frozen=True)
class AgentContract:
    role: str
    task_id: str
    module: ModuleType
    inputs: tuple[str, ...]
    outputs: tuple[str, ...]
    task: str


AGENT_CONTRACTS = (
    AgentContract(
        role="TelemetryAgent",
        task_id="telemetry",
        module=telemetry,
        inputs=(),
        outputs=("runtime_evidence",),
        task=(
            "TelemetryAgent: acquire configured telemetry and publish runtime_evidence. "
            "Preserve unknown exposure/deserialization as null: absent observations are a source "
            "limitation, not incomplete task execution. Do not infer missing facts."
        ),
    ),
    AgentContract(
        role="VulnerabilityAgent",
        task_id="vulnerability",
        module=vulnerability,
        inputs=("runtime_evidence",),
        outputs=("vulnerability_report",),
        task=(
            "VulnerabilityAgent: read runtime_evidence for the software/version lookup and publish "
            "a separate vulnerability_report. Preserve missing CVSS/confidence as null and CWE as "
            "an empty list. Report bounded no_findings or unresolved lookup outcomes faithfully; "
            "missing source metadata is not a failed task and must not be fabricated."
        ),
    ),
    AgentContract(
        role="CountermeasureAgent",
        task_id="countermeasure",
        module=countermeasure,
        inputs=("runtime_evidence", "vulnerability_report"),
        outputs=("candidate_strategies",),
        task=(
            "CountermeasureAgent: read runtime_evidence and vulnerability_report separately via "
            "get_context, acquire the SBOM/OSV context when configured, then generate and publish "
            "candidate_strategies. When package verification is required, call "
            "prepare_package_verification and preserve its pending verification_requests. "
            "If the report has no findings, publish strategies=[]; "
            "this is the required successful result, not missing work."
        ),
    ),
    AgentContract(
        role="StrategicAgent",
        task_id="strategic",
        module=strategic,
        inputs=("runtime_evidence", "vulnerability_report", "candidate_strategies"),
        outputs=(
            "argumentation_graph",
            "ranking",
            "semantic_validation",
            "final_decision",
            "provenance",
        ),
        task=(
            "StrategicAgent: read runtime_evidence, vulnerability_report and candidate_strategies "
            "separately via get_context, preserving their producers; build graph, rank, validate "
            "in order, publish decision and provenance. With no candidates, publish empty graph, "
            "ranking and semantic report, select null and record provenance; "
            "skip validation calls. "
            "An empty ranking is legitimate only when the candidate set is empty. A failed or "
            "incomplete backend response must not become an abstention. "
            "After rank_graph, CALL publish_final_decision(selected_strategy_id=null, "
            "explanation=...) "
            "when there are no candidates; this tool also creates the empty semantic report. "
            "Then CALL record_provenance with {}. Both must be real tool calls before TaskResult."
        ),
    ),
)

# Le viste sono di sola lettura. Il DAG passato a CAMEL e le condizioni degli
# handler usano gli stessi contratti, senza una seconda lista di prerequisiti.
ROLE_INPUTS = MappingProxyType({c.role: c.inputs for c in AGENT_CONTRACTS})
ROLE_OUTPUTS = MappingProxyType({c.role: c.outputs for c in AGENT_CONTRACTS})
ARTIFACT_OWNERS = MappingProxyType(
    {artifact: c.role for c in AGENT_CONTRACTS for artifact in c.outputs}
)
_TASK_BY_ARTIFACT = {artifact: c.task_id for c in AGENT_CONTRACTS for artifact in c.outputs}
TASK_DEPENDENCIES = MappingProxyType(
    {
        c.task_id: tuple(dict.fromkeys(_TASK_BY_ARTIFACT[artifact] for artifact in c.inputs))
        for c in AGENT_CONTRACTS
    }
)
