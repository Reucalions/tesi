"""Checkpoint di ranking nativo: non costituisce una raccomandazione finalizzata."""

from typing import Literal

from pydantic import Field, model_validator

from thesis_agents.canonical.contracts import SHA256, CandidateBinding
from thesis_agents.mcp.shared_contracts import (
    CVE,
    Digest,
    RankRemediationsResponse,
    SharedDecision,
    SharedProvenance,
    WireModel,
)
from thesis_agents.schemas.base import Identifier, Text, require_unique


class NativeRankingSettings(WireModel):
    contract: Literal["shared-strategic-ranking-v1"] = "shared-strategic-ranking-v1"
    tenant_id: Text
    knowledge_snapshot_id: Text
    knowledge_snapshot_digest: Digest
    ontology_digest: Digest


class NativeCVERanking(WireModel):
    cve_id: CVE
    bindings: list[CandidateBinding] = Field(min_length=1)
    ranking: RankRemediationsResponse
    decision_readback: SharedDecision
    provenance_readback: SharedProvenance

    @model_validator(mode="after")
    def correlate(self):
        rank, decision, provenance = (
            self.ranking,
            self.decision_readback,
            self.provenance_readback,
        )
        require_unique([b.strategy_id for b in self.bindings], "MAS IDs per CVE")
        require_unique([b.ontology_individual for b in self.bindings], "KG IDs per CVE")
        if (
            rank.cve_id != self.cve_id
            or any(b.cve_id != self.cve_id for b in self.bindings)
            or {b.ontology_individual for b in self.bindings}
            != {row.id for row in rank.ranked_strategies}
            or rank.status != "CURRENT"
            or decision.status != rank.status
            or decision.cve_id != rank.cve_id
            or decision.tenant_id != rank.tenant_id
            or decision.revision != rank.revision
            or decision.ranked_strategies != rank.ranked_strategies
            or decision.input_digest != rank.slsa_assurance.input_digest
            or decision.ontology_digest != rank.slsa_assurance.ontology_digest
        ):
            raise ValueError("Native ranking, bindings and decision readback differ")
        for readback in (decision, provenance):
            if (
                readback.decision_id != rank.decision_id
                or readback.knowledge_snapshot_id != rank.knowledge_snapshot_id
                or readback.knowledge_snapshot_digest != rank.knowledge_snapshot_digest
                or readback.slsa_assurance != rank.slsa_assurance
            ):
                raise ValueError("Native readback differs from original ranking")
        return self


class NativeStrategicRanking(WireModel):
    contract: Literal["native-strategic-ranking-v1"] = "native-strategic-ranking-v1"
    run_id: Identifier
    asset_id: Identifier
    preparation_sha256: SHA256
    aln_ontology_sha256: SHA256
    source_ontology_sha256: SHA256
    settings: NativeRankingSettings
    backend_kind: Literal["mock", "real"]
    results: list[NativeCVERanking] = Field(min_length=1)
    deployment_verified: Literal[False] = False
    semantic_validation: Literal["pending"] = "pending"
    recommendation: Literal["pending"] = "pending"
    provenance_scope: Literal["saas_ranking_record"] = "saas_ranking_record"
    action_execution: Literal["not_performed"] = "not_performed"

    @model_validator(mode="after")
    def scope(self):
        require_unique([r.cve_id for r in self.results], "native ranking CVEs")
        require_unique([r.ranking.decision_id for r in self.results], "SaaS decision IDs")
        for result in self.results:
            rank = result.ranking
            if (
                rank.tenant_id != self.settings.tenant_id
                or rank.knowledge_snapshot_id != self.settings.knowledge_snapshot_id
                or rank.knowledge_snapshot_digest != self.settings.knowledge_snapshot_digest
                or rank.slsa_assurance.ontology_digest != self.settings.ontology_digest
            ):
                raise ValueError("SaaS ranking differs from configured tenant/snapshot/ontology")
        return self
