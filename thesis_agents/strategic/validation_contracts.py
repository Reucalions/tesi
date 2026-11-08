"""Binding operativi/IRI e checkpoint di validazione, senza selezione o applicazione."""

from typing import Literal

from pydantic import Field, model_validator

from thesis_agents.canonical.contracts import SHA256, Individual
from thesis_agents.mcp.operational_contracts import (
    AbsoluteIRI,
    ConstraintMapping,
    OperationalContext,
    verify_operational_assessment,
)
from thesis_agents.mcp.shared_contracts import (
    CVE,
    SharedValidation,
    ValidateCountermeasureRequest,
    WireModel,
)
from thesis_agents.schemas.base import Identifier, Text, require_unique
from thesis_agents.schemas.countermeasure import Action


class ValidationBinding(WireModel):
    cve_id: CVE
    strategy_id: Identifier
    ontology_individual: Individual
    countermeasure_iri: AbsoluteIRI


class CandidateConstraintMapping(ConstraintMapping):
    strategy_id: Identifier


class ValidationProfile(WireModel):
    contract: Literal["native-validation-profile-v1"] = "native-validation-profile-v1"
    run_id: Identifier
    asset_id: Identifier
    ranking_sha256: SHA256
    ontology_key: Text
    asset_iri: AbsoluteIRI
    bindings: list[ValidationBinding] = Field(min_length=1)
    available_capabilities: list[Text] = Field(max_length=64)
    prohibited_actions: list[Action] = Field(max_length=4)
    constraint_mappings: list[CandidateConstraintMapping] = Field(max_length=64)
    policy_source: Text
    iri_binding_origin: Literal["operator_configuration"] = "operator_configuration"

    @model_validator(mode="after")
    def unique_bindings(self):
        require_unique([f"{b.cve_id}:{b.strategy_id}" for b in self.bindings], "IRI bindings")
        require_unique(
            [f"{b.cve_id}:{b.countermeasure_iri}" for b in self.bindings], "IRI targets per CVE"
        )
        require_unique(
            [f"{m.strategy_id}:{m.constraint}" for m in self.constraint_mappings],
            "constraint mappings",
        )
        require_unique(self.available_capabilities, "available capabilities")
        require_unique(self.prohibited_actions, "prohibited actions")
        return self


class NativeValidationAttempt(WireModel):
    cve_id: CVE
    strategy_id: Identifier
    ontology_individual: Individual
    ranking_decision_id: Text
    request: ValidateCountermeasureRequest
    response: SharedValidation

    @model_validator(mode="after")
    def correlate(self):
        context = self.request.operational_context
        if context is None or self.response.operational is None:
            raise ValueError("Native validation requires the operational context and assessment")
        if (
            context.cve_id != self.cve_id
            or context.strategy_id != self.strategy_id
            or context.ontology_individual != self.ontology_individual
            or context.ranking_decision_id != self.ranking_decision_id
            or self.request.asset_iri != self.response.reasoning.resource_iri
            or self.request.countermeasure_iri != self.response.reasoning.request_iri
            or self.request.ontology_id != self.response.reasoning.ontology_key
        ):
            raise ValueError("Validation identity/IRI differs from request/bindings")
        verify_operational_assessment(context, self.response.operational)
        return self


class NativeStrategicValidation(WireModel):
    contract: Literal["native-strategic-validation-v1"] = "native-strategic-validation-v1"
    run_id: Identifier
    asset_id: Identifier
    ranking_sha256: SHA256
    profile_sha256: SHA256
    attempts: list[NativeValidationAttempt] = Field(min_length=1)
    recommendation: Literal["pending"] = "pending"
    shared_finalization: Literal["pending"] = "pending"
    deployment_verified: Literal[False] = False
    action_execution: Literal["not_performed"] = "not_performed"

    @model_validator(mode="after")
    def scope(self):
        require_unique(
            [f"{a.cve_id}:{a.strategy_id}" for a in self.attempts], "validation attempts"
        )
        for attempt in self.attempts:
            context: OperationalContext = attempt.request.operational_context
            if context.run_id != self.run_id or context.asset_id != self.asset_id:
                raise ValueError("Validation context belongs to another run/asset")
        return self
