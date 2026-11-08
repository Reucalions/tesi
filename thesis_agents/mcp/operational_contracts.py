"""Contesto operativo SaaS: policy esplicita, distinta dall'inferenza Tiny-ME."""

import re
from typing import Annotated, Literal
from urllib.parse import urlsplit

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, StrictBool, model_validator

from thesis_agents.mcp.client import digest
from thesis_agents.schemas.base import Identifier, Text, require_unique
from thesis_agents.schemas.countermeasure import Action

POLICY_ID = "operational-action-policy-v1"
ACTION_REQUIREMENTS = {
    "upgrade": ["maintenance_window", "package_upgrade"],
    "isolate": ["network_isolation"],
    "block_deployment": ["deployment_control"],
    "monitor": ["monitoring"],
}
POLICY_DIGEST = "sha256:" + digest(ACTION_REQUIREMENTS)
Digest = Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")]
Status = Literal["accepted", "requires_prerequisites", "rejected", "requires_review"]


def absolute_iri(value):
    if re.search(r'[\s<>"{}|^`\\]', value) or not value.startswith(("http://", "https://", "urn:")):
        raise ValueError("An explicit absolute HTTP(S) or URN IRI is required")
    parsed = urlsplit(value)
    if (
        parsed.scheme in ("http", "https")
        and (not parsed.hostname or parsed.username is not None or parsed.password is not None)
    ) or (parsed.scheme == "urn" and not parsed.path):
        raise ValueError("Invalid absolute IRI")
    return value


AbsoluteIRI = Annotated[Text, AfterValidator(absolute_iri)]


class OperationalModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class ConstraintMapping(OperationalModel):
    constraint: Text
    required_capabilities: list[Text] = Field(min_length=1, max_length=64)

    @model_validator(mode="after")
    def unique_requirements(self):
        require_unique(self.required_capabilities, "mapped requirements")
        return self


class OperationalContext(OperationalModel):
    contract: Literal["operational-context-v1"] = "operational-context-v1"
    run_id: Identifier
    asset_id: Identifier
    cve_id: Annotated[str, Field(pattern=r"^CVE-\d{4}-\d{4,}$")]
    strategy_id: Identifier
    ranking_decision_id: Text
    ontology_individual: Text
    action: Action
    prerequisites: list[Text] = Field(max_length=64)
    constraints: list[Text] = Field(max_length=64)
    available_capabilities: list[Text] = Field(max_length=64)
    prohibited_actions: list[Action] = Field(max_length=4)
    constraint_mappings: list[ConstraintMapping] = Field(max_length=64)
    evidence_digest: Digest
    candidates_digest: Digest
    policy_source: Text
    policy_id: Literal["operational-action-policy-v1"] = POLICY_ID
    policy_digest: Digest = POLICY_DIGEST

    @model_validator(mode="after")
    def scope(self):
        for name in (
            "prerequisites",
            "constraints",
            "available_capabilities",
            "prohibited_actions",
        ):
            require_unique(getattr(self, name), name)
        mapped = [row.constraint for row in self.constraint_mappings]
        require_unique(mapped, "constraint mappings")
        if not set(mapped) <= set(self.constraints) or self.policy_digest != POLICY_DIGEST:
            raise ValueError("Operational mappings or policy digest differ from contract")
        return self


class OperationalAssessment(OperationalModel):
    contract: Literal["operational-assessment-v1"] = "operational-assessment-v1"
    context_digest: Digest
    policy_id: Literal["operational-action-policy-v1"]
    policy_digest: Digest
    status: Status
    required_capabilities: list[Text]
    missing_capabilities: list[Text]
    prohibited_action: StrictBool
    unassessed_constraints: list[Text]
    evaluator: Literal["saas_operational_policy"] = "saas_operational_policy"


def verify_operational_assessment(context, result):
    """Verify contract arithmetic; the SaaS is the evaluator, not an LLM/local fallback."""
    required = sorted(
        set(ACTION_REQUIREMENTS[context.action])
        | set(context.prerequisites)
        | {
            capability
            for mapping in context.constraint_mappings
            for capability in mapping.required_capabilities
        }
    )
    missing = sorted(set(required) - set(context.available_capabilities))
    prohibited = context.action in context.prohibited_actions
    mapped = {mapping.constraint for mapping in context.constraint_mappings}
    unassessed = sorted(set(context.constraints) - mapped)
    expected = (
        "rejected"
        if prohibited
        else "requires_prerequisites"
        if missing
        else "requires_review"
        if unassessed
        else "accepted"
    )
    if (
        result.context_digest != "sha256:" + digest(context.model_dump(mode="json"))
        or result.policy_id != context.policy_id
        or result.policy_digest != context.policy_digest
        or result.required_capabilities != required
        or result.missing_capabilities != missing
        or result.prohibited_action != prohibited
        or result.unassessed_constraints != unassessed
        or result.status != expected
    ):
        raise ValueError("Operational response contradicts the submitted context/policy")


def effective_status(semantic, operational):
    statuses = {semantic, operational}
    for status in ("rejected", "requires_prerequisites", "requires_review"):
        if status in statuses:
            return status
    return "accepted"
