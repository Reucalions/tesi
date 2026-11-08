"""Local dry-run recommendation: first effectively acceptable native candidate per CVE."""

from typing import Literal

from pydantic import Field, model_validator

from thesis_agents.canonical.contracts import SHA256
from thesis_agents.mcp.shared_contracts import CVE, NativeRankedStrategy, WireModel
from thesis_agents.schemas.base import Identifier, Text, require_unique
from thesis_agents.strategic.validation_contracts import NativeValidationAttempt

Outcome = Literal["recommended", "requires_prerequisites", "requires_review", "no_valid_strategy"]


class CandidateAssessment(WireModel):
    ranking: NativeRankedStrategy
    validation: NativeValidationAttempt
    disposition: Literal["selected", "not_acceptable", "lower_ranked_acceptable"]

    @model_validator(mode="after")
    def correlate(self):
        accepted = self.validation.response.effective_status == "accepted"
        if self.ranking.id != self.validation.ontology_individual or accepted != (
            self.disposition != "not_acceptable"
        ):
            raise ValueError("Candidate disposition differs from native identity/effective status")
        return self


def selection_outcome(attempts):
    statuses = {a.response.effective_status for a in attempts}
    if "accepted" in statuses:
        return "recommended"
    if "requires_review" in statuses:
        return "requires_review"
    if "requires_prerequisites" in statuses:
        return "requires_prerequisites"
    return "no_valid_strategy"


class CVERecommendation(WireModel):
    cve_id: CVE
    ranking_decision_id: Text
    outcome: Outcome
    selected_strategy_id: Identifier | None
    candidates: list[CandidateAssessment] = Field(min_length=1)

    @model_validator(mode="after")
    def first_acceptable(self):
        rows = self.candidates
        require_unique([r.validation.strategy_id for r in rows], "recommendation strategies")
        require_unique([r.ranking.id for r in rows], "recommendation KG IDs")
        if [r.ranking.rank for r in rows] != list(range(1, len(rows) + 1)) or rows != sorted(
            rows, key=lambda r: (-r.ranking.score, r.ranking.id)
        ):
            raise ValueError("Recommendation must preserve native ranks, scores and tie order")
        accepted = [r for r in rows if r.validation.response.effective_status == "accepted"]
        selected = accepted[0] if accepted else None
        if self.selected_strategy_id != (selected.validation.strategy_id if selected else None):
            raise ValueError("Selected strategy is not the first effectively acceptable candidate")
        if self.outcome != selection_outcome([r.validation for r in rows]):
            raise ValueError("Recommendation outcome differs from validation results")
        for row in rows:
            expected = (
                "selected"
                if row is selected
                else "lower_ranked_acceptable"
                if row.validation.response.effective_status == "accepted"
                else "not_acceptable"
            )
            if (
                row.disposition != expected
                or row.validation.cve_id != self.cve_id
                or row.validation.ranking_decision_id != self.ranking_decision_id
            ):
                raise ValueError("Candidate disposition or ranking/CVE lineage differs")
        return self


class NativeStrategicRecommendation(WireModel):
    contract: Literal["native-strategic-recommendation-v1"] = "native-strategic-recommendation-v1"
    run_id: Identifier
    asset_id: Identifier
    ranking_sha256: SHA256
    validation_sha256: SHA256
    validation_profile_sha256: SHA256
    backend_kind: Literal["mock", "real"]
    results: list[CVERecommendation] = Field(min_length=1)
    selection_policy: Literal["first-effective-accepted-per-cve-v1"] = (
        "first-effective-accepted-per-cve-v1"
    )
    decision_scope: Literal["per_cve"] = "per_cve"
    status: Literal["dry_run_completed"] = "dry_run_completed"
    shared_finalization: Literal["pending"] = "pending"
    provenance_scope: Literal["local_artifact_lineage"] = "local_artifact_lineage"
    deployment_verified: Literal[False] = False
    action_execution: Literal["not_performed"] = "not_performed"

    @model_validator(mode="after")
    def scope(self):
        require_unique([r.cve_id for r in self.results], "recommendation CVEs")
        for result in self.results:
            for row in result.candidates:
                context = row.validation.request.operational_context
                if context.run_id != self.run_id or context.asset_id != self.asset_id:
                    raise ValueError("Recommendation belongs to another run/asset")
        return self
