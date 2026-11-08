"""Wire SaaS/MCP condiviso, distinto dagli artefatti MVP e dal grafo canonico.

Gli score di ranking restano nativi. Nessuna conversione implicita verso UnitScore,
nessuna ricostruzione di un reasoner o di una registrazione della decisione MAS.
"""

import json
from importlib.resources import files
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool, model_validator

from thesis_agents.mcp.operational_contracts import (
    OperationalAssessment,
    OperationalContext,
    Status,
    absolute_iri,
    effective_status,
)
from thesis_agents.schemas.base import Text, require_unique

Finite = Annotated[float, Field(strict=True, allow_inf_nan=False)]
Nonnegative = Annotated[float, Field(strict=True, ge=0, allow_inf_nan=False)]
Digest = Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")]
CVE = Annotated[str, Field(pattern=r"^CVE-\d{4}-\d{4,}$")]
PositiveInt = Annotated[int, Field(strict=True, ge=1)]


class WireModel(BaseModel):
    model_config = ConfigDict(extra="forbid", populate_by_name=True)


class SharedCandidate(WireModel):
    id: Text
    name: Text
    description: str | None = None
    d3fend_technique: str | None = None


class SharedAssetContext(WireModel):
    asset_iri: Text | None = Field(default=None, alias="assetIri")
    product_name: Text | None = Field(default=None, alias="productName")
    vendor: Text | None = None
    version: Text | None = None
    cpe: Text | None = None


class SharedGraphNode(WireModel):
    id: Text
    type: Text


class SharedGraphEdge(WireModel):
    source: Text = Field(alias="from")
    target: Text = Field(alias="to")


class SharedGraph(WireModel):
    """Topologia nativa; significato degli archi e pesi spettano all'adapter canonico."""

    nodes: list[SharedGraphNode] = Field(min_length=1)
    edges: list[SharedGraphEdge]

    @model_validator(mode="after")
    def references(self):
        ids = [node.id for node in self.nodes]
        require_unique(ids, "shared graph node IDs")
        if any(
            e.source not in ids or e.target not in ids or e.source == e.target for e in self.edges
        ):
            raise ValueError("Invalid shared graph edge")
        return self


class RankRemediationsRequest(WireModel):
    cve_id: CVE
    candidates: list[SharedCandidate] = Field(min_length=1)
    asset_context: SharedAssetContext | None = None
    graph: SharedGraph | None = None
    knowledge_snapshot_id: Text | None = None
    ontology_version: Text | None = None

    @model_validator(mode="after")
    def candidate_scope(self):
        ids = [candidate.id for candidate in self.candidates]
        require_unique(ids, "shared candidate IDs")
        require_unique([candidate.name for candidate in self.candidates], "shared candidate names")
        if self.graph is not None and {
            node.id for node in self.graph.nodes if node.type == "strategy"
        } != set(ids):
            raise ValueError("Shared graph strategies must match candidate IDs")
        return self

    def wire_payload(self) -> dict:
        return self.model_dump(mode="json", by_alias=True, exclude_none=True)

    def rest_payload(self) -> dict:
        wire = self.wire_payload()
        result = {"cveId": self.cve_id, "candidates": []}
        for candidate in wire["candidates"]:
            candidate = dict(candidate)
            if "d3fend_technique" in candidate:
                candidate["d3fendTechnique"] = candidate.pop("d3fend_technique")
            result["candidates"].append(candidate)
        for source, target in (
            ("asset_context", "assetContext"),
            ("graph", "graph"),
            ("knowledge_snapshot_id", "knowledgeSnapshotId"),
            ("ontology_version", "ontologyVersion"),
        ):
            if source in wire:
                result[target] = wire[source]
        return result


class ValidateCountermeasureRequest(WireModel):
    asset_iri: Text
    countermeasure_iri: Text
    ontology_id: Text | None = None
    operational_context: OperationalContext | None = None

    @model_validator(mode="after")
    def explicit_context_iris(self):
        if self.operational_context is not None:
            absolute_iri(self.asset_iri)
            absolute_iri(self.countermeasure_iri)
            if self.ontology_id is None:
                raise ValueError("Context-aware validation requires an explicit ontology key")
        return self


class DecisionRequest(WireModel):
    decision_id: Text


class Assurance(WireModel):
    builder_id: Text = Field(alias="builderId")
    chaincode_digest: Annotated[str, Field(pattern=r"^(sha256:[0-9a-f]{64})?$")] = Field(
        alias="chaincodeDigest"
    )
    ontology_digest: Digest = Field(alias="ontologyDigest")
    input_digest: Digest = Field(alias="inputDigest")
    verified: StrictBool
    artifacts: list[dict[str, Any]] | None = None

    @model_validator(mode="after")
    def verification(self):
        if self.verified and not self.chaincode_digest:
            raise ValueError("Verified assurance requires a chaincode digest")
        return self


class NativeRankedStrategy(WireModel):
    rank: PositiveInt
    id: Text
    name: Text
    score: Finite
    d3fend_technique: str | None = Field(default=None, alias="d3fendTechnique")
    explanation: dict[str, Any] | None = None


class DecisionFields(WireModel):
    decision_id: Text = Field(alias="decisionId")
    cve_id: CVE = Field(alias="cveId")
    tenant_id: Text = Field(alias="tenantId")
    status: Literal["CURRENT", "STALE", "RECOMPUTED"]
    revision: PositiveInt
    ranked_strategies: list[NativeRankedStrategy] = Field(alias="rankedStrategies", min_length=1)
    knowledge_snapshot_id: Text | None = Field(default=None, alias="knowledgeSnapshotId")
    knowledge_snapshot_digest: Digest | None = Field(default=None, alias="knowledgeSnapshotDigest")

    @model_validator(mode="after")
    def ranking(self):
        rows = self.ranked_strategies
        require_unique([row.id for row in rows], "native ranked candidate IDs")
        if [row.rank for row in rows] != list(range(1, len(rows) + 1)) or rows != sorted(
            rows, key=lambda row: (-row.score, row.id)
        ):
            raise ValueError("Invalid native ranking order or ranks")
        return self


class RankRemediationsResponse(DecisionFields):
    slsa_assurance: Assurance = Field(alias="slsaAssurance")
    annotated_graph_key: Text | None = Field(default=None, alias="annotatedGraphKey")
    timestamp: Text


class SharedDecision(DecisionFields):
    input_digest: Digest = Field(alias="inputDigest")
    ontology_digest: Digest = Field(alias="ontologyDigest")
    slsa_assurance: Assurance | None = Field(default=None, alias="slsaAssurance")
    stale_reason: str | None = Field(default=None, alias="staleReason")
    previous_revision_id: str | None = Field(default=None, alias="previousRevisionId")
    created_at: Text = Field(alias="createdAt")
    updated_at: Text = Field(alias="updatedAt")

    @model_validator(mode="after")
    def assurance_consistency(self):
        if self.slsa_assurance is not None and (
            self.input_digest != self.slsa_assurance.input_digest
            or self.ontology_digest != self.slsa_assurance.ontology_digest
        ):
            raise ValueError("Decision digests differ from original assurance")
        return self


class NativeAffinity(WireModel):
    resource_iri: Text = Field(alias="resourceIRI")
    score: Annotated[float, Field(strict=True, ge=0, le=100, allow_inf_nan=False)]
    top_penalty: Nonnegative = Field(alias="topPenalty")
    abduction_penalty: Nonnegative = Field(alias="abductionPenalty")
    contraction_penalty: Nonnegative = Field(alias="contractionPenalty")
    hypothesis: str
    give_up: str = Field(alias="giveUp")
    keep: str


class AffinityReasoning(WireModel):
    contract: Literal["explain-affinity-v1"]
    ontology_key: Text = Field(alias="ontologyKey")
    resource_iri: Text = Field(alias="resourceIRI")
    request_iri: Text = Field(alias="requestIRI")
    native: NativeAffinity


class SharedValidation(WireModel):
    valid: StrictBool
    status: Literal["accepted", "requires_prerequisites", "rejected"]
    affinity_score: Annotated[float, Field(strict=True, ge=0, le=1, allow_inf_nan=False)] = Field(
        alias="affinityScore"
    )
    conflict_penalty: Nonnegative = Field(alias="conflictPenalty")
    missing_features: list[Text] = Field(alias="missingFeatures")
    bonus_features: list[Text] = Field(alias="bonusFeatures", max_length=0)
    bonus_evaluated: Literal[False] = Field(alias="bonusEvaluated")
    explanation: Text
    timestamp: Text
    reasoning: AffinityReasoning
    operational: OperationalAssessment | None = None
    effective_status: Status | None = Field(default=None, alias="effectiveStatus")

    @model_validator(mode="after")
    def native_consistency(self):
        native = self.reasoning.native
        # This wire contract freezes the existing ExplainAffinity v1 Go score,
        # distinct from BWAF relation weights and native acceptability ranking.
        penalty = (
            native.abduction_penalty if native.abduction_penalty > 0 else native.contraction_penalty
        )
        if abs(native.score - max(0, 100 - penalty)) > 1e-9:
            raise ValueError("ExplainAffinity score differs from its native penalty")
        compatible = bool(native.hypothesis.strip()) and not native.give_up.strip()
        incompatible = bool(native.give_up.strip()) and not native.hypothesis.strip()
        expected_missing = [native.hypothesis] if native.abduction_penalty > 0 else []
        if (not compatible and not incompatible) or (
            native.resource_iri != self.reasoning.resource_iri
            or self.affinity_score != native.score / 100
            or self.conflict_penalty != native.contraction_penalty
            or self.missing_features != expected_missing
            or (compatible and native.contraction_penalty > 0)
            or (incompatible and native.abduction_penalty > 0)
        ):
            raise ValueError("Semantic response differs from native reasoning")
        accepted = (
            compatible and not expected_missing and native.top_penalty == 0 and native.score > 0
        )
        status = (
            "accepted"
            if accepted
            else "requires_prerequisites"
            if compatible and expected_missing
            else "rejected"
        )
        if self.valid != accepted or self.status != status:
            raise ValueError("Semantic status contradicts conditions or conflicts")
        if (self.operational is None) != (self.effective_status is None):
            raise ValueError("Operational result and effective status must appear together")
        if self.operational is not None and self.effective_status != effective_status(
            self.status, self.operational.status
        ):
            raise ValueError("Effective result contradicts semantic/operational results")
        return self


class SharedProvenance(WireModel):
    decision_id: Text = Field(alias="decisionId")
    context: dict[str, str]
    entities: list[dict[str, Any]]
    activities: list[dict[str, Any]]
    agents: list[dict[str, Any]]
    relations: list[dict[str, Any]]
    slsa_assurance: Assurance = Field(alias="slsaAssurance")
    knowledge_snapshot_id: Text | None = Field(default=None, alias="knowledgeSnapshotId")
    knowledge_snapshot_digest: Digest | None = Field(default=None, alias="knowledgeSnapshotDigest")


REQUESTS = {
    "rank_remediations": RankRemediationsRequest,
    "validate_countermeasure": ValidateCountermeasureRequest,
    "get_decision": DecisionRequest,
    "get_provenance": DecisionRequest,
}
RESPONSES = {
    "rank_remediations": RankRemediationsResponse,
    "validate_countermeasure": SharedValidation,
    "get_decision": SharedDecision,
    "get_provenance": SharedProvenance,
}


def shared_contracts() -> dict:
    # Snapshot della discovery del bridge, senza descrizioni. L'assenza di
    # outputSchema e esplicita: gli output sono sempre validati dai modelli sopra.
    return json.loads(
        files("thesis_agents").joinpath("data/shared-mcp-schemas-v1.json").read_text()
    )
