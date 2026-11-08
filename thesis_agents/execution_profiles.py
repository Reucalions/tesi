"""Explicit mockup/real backend choice, independent of model inference and Git branches."""

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from thesis_agents.backends import BackendSettings, LocalBackend
from thesis_agents.canonical.contracts import Assessments, CandidateBinding, PreparationRequest
from thesis_agents.canonical.preparation import PreparationSettings
from thesis_agents.mcp.operational_contracts import AbsoluteIRI
from thesis_agents.mcp.settings import MCPConnectionSettings
from thesis_agents.mcp.shared_client import SharedMCPProfile
from thesis_agents.schemas.base import Text
from thesis_agents.schemas.countermeasure import Action
from thesis_agents.strategic.contracts import NativeRankingSettings
from thesis_agents.strategic.validation_contracts import (
    CandidateConstraintMapping,
    ValidationBinding,
    ValidationProfile,
)
from thesis_agents.telemetry.settings import StaticSource, TelemetryHTTPSettings
from thesis_agents.tools.sbom_http import NoSupplyChainSource, SupplyChainHTTPSettings


class ProfileModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


def require_mockup(settings):
    if settings is not None and (
        not isinstance(settings.telemetry, StaticSource)
        or not isinstance(settings.countermeasure_input, NoSupplyChainSource)
        or not all(
            isinstance(getattr(settings, name), LocalBackend)
            for name in ("vulnerability", "ranking", "semantic", "provenance")
        )
    ):
        raise ValueError("backend-mode=mockup requires only local mock backends and static input")


class RealSources(ProfileModel):
    telemetry: TelemetryHTTPSettings
    vulnerability: MCPConnectionSettings
    countermeasure_input: SupplyChainHTTPSettings
    vulnerability_adapter: Literal["lookup-v1", "cve2owl-v1", "ubuntu-package-v1"]
    cti_dataset_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    ubuntu_sources_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def real_sources(self):
        if self.vulnerability.expected_kind != "real":
            raise ValueError("Real mode requires a real CTI backend")
        if (
            self.countermeasure_input.expected_kind != "live"
            or self.countermeasure_input.sbom_kind != "provided"
        ):
            raise ValueError("Real mode requires a provided SBOM and live OSV service")
        # Reuse existing CTI compatibility checks; no runtime tools are instantiated here.
        BackendSettings.model_validate(self.model_dump())
        return self


class PreparationScope(ProfileModel):
    assessments: Assessments
    bindings: list[CandidateBinding] = Field(min_length=1)


class ValidationScope(ProfileModel):
    ontology_key: Text
    asset_iri: AbsoluteIRI
    bindings: list[ValidationBinding] = Field(min_length=1)
    available_capabilities: list[Text]
    prohibited_actions: list[Action]
    constraint_mappings: list[CandidateConstraintMapping]
    policy_source: Text


class RealExecutionProfile(ProfileModel):
    contract: Literal["real-execution-v1"] = "real-execution-v1"
    sources: RealSources
    preparation: PreparationSettings
    preparation_scope: PreparationScope
    shared: SharedMCPProfile
    ranking: NativeRankingSettings
    validation: ValidationScope

    @model_validator(mode="after")
    def coherent_scope(self):
        if self.shared.connection.expected_kind != "real":
            raise ValueError("Real mode requires the shared SaaS bridge configured as real")
        if self.preparation.knowledge_snapshot_id != self.ranking.knowledge_snapshot_id:
            raise ValueError("Preparation/ranking snapshot IDs differ")
        expected = {
            (b.cve_id, b.strategy_id, b.ontology_individual)
            for b in self.preparation_scope.bindings
        }
        actual = {
            (b.cve_id, b.strategy_id, b.ontology_individual) for b in self.validation.bindings
        }
        if expected != actual:
            raise ValueError("Preparation and validation bindings must match exactly")
        PreparationRequest(
            run_id="profile-check",
            asset_id="profile-check",
            input_digests={
                name: "0" * 64
                for name in ("runtime_evidence", "vulnerability_report", "candidate_strategies")
            },
            **self.preparation_scope.model_dump(),
        )
        ValidationProfile(
            run_id="profile-check",
            asset_id="profile-check",
            ranking_sha256="0" * 64,
            **self.validation.model_dump(),
        )
        return self

    @classmethod
    def load(cls, path):
        return cls.model_validate_json(path.read_bytes())
