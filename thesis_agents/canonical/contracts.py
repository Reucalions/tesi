"""Contratto del generatore Bottalico e rappresentazione canonica senza pesi inventati."""

from typing import Annotated, Literal

from pydantic import Field, StrictBool, model_validator

from thesis_agents.mcp.shared_contracts import CVE, RankRemediationsRequest, WireModel
from thesis_agents.schemas.base import Identifier, Text, require_unique

SHA256 = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
Individual = Annotated[str, Field(pattern=r"^[A-Za-z_][A-Za-z0-9_.-]*$")]
InputName = Literal["runtime_evidence", "vulnerability_report", "candidate_strategies"]


class ObservedAsset(WireModel):
    product: Text
    version: Text
    vendor: Text | None = None
    asset_type: Literal["application", "os", "hardware"] | None = None


class EvaluatedVersion(WireModel):
    evaluated: StrictBool
    matched_asset_version: StrictBool
    vulnerability_status: Literal["vulnerable"]
    version_iri: Individual

    @model_validator(mode="after")
    def confirmed(self):
        if not (self.evaluated and self.matched_asset_version):
            raise ValueError("Preparation requires a confirmed evaluated version match")
        return self


class AffectedEntry(WireModel):
    cve_id: CVE
    affected_iri: Individual
    vulnerability_status: Literal["vulnerable"]
    version_rules: list[EvaluatedVersion] = Field(min_length=1)


class ConfirmedMatch(WireModel):
    confidence: Literal["high"]
    affected_entries: list[AffectedEntry] = Field(min_length=1)


class AssetAssessment(WireModel):
    asset: ObservedAsset
    matches: list[ConfirmedMatch] = Field(min_length=1)


class Assessments(WireModel):
    results: list[AssetAssessment] = Field(min_length=1)


class CandidateBinding(WireModel):
    cve_id: CVE
    strategy_id: Identifier
    ontology_individual: Individual


class PreparationRequest(WireModel):
    contract: Literal["semantic-preparation-v1"] = "semantic-preparation-v1"
    run_id: Identifier
    asset_id: Identifier
    input_digests: dict[InputName, SHA256]
    assessments: Assessments
    bindings: list[CandidateBinding] = Field(min_length=1)

    @model_validator(mode="after")
    def scope(self):
        if set(self.input_digests) != {
            "runtime_evidence",
            "vulnerability_report",
            "candidate_strategies",
        }:
            raise ValueError("All three MAS artifact digests are required")
        entries = [
            e for a in self.assessments.results for m in a.matches for e in m.affected_entries
        ]
        cves = {e.cve_id for e in entries}
        if cves != {b.cve_id for b in self.bindings}:
            raise ValueError("Assessment CVEs and binding CVEs must match exactly")
        require_unique(
            [f"{b.cve_id}:{b.strategy_id}" for b in self.bindings], "CVE/candidate bindings"
        )
        require_unique(
            [f"{b.cve_id}:{b.ontology_individual}" for b in self.bindings], "CVE/KG bindings"
        )
        return self


class CanonicalEdge(WireModel):
    source: Individual = Field(alias="from")
    target: Individual = Field(alias="to")
    origin: Literal["kg_remediation", "generator_comparison_ring"]
    polarity: Literal["deferred_to_shared_reasoner"] = "deferred_to_shared_reasoner"


class CanonicalGraph(WireModel):
    cve_id: CVE
    topology: Literal["bottalico-directed-ring-v1"] = "bottalico-directed-ring-v1"
    ranking_request: RankRemediationsRequest
    edge_sources: list[CanonicalEdge]

    @model_validator(mode="after")
    def trace_edges(self):
        graph = self.ranking_request.graph
        if graph is None or self.ranking_request.cve_id != self.cve_id:
            raise ValueError("Canonical graph requires an explicit native graph for its CVE")
        names = sorted(candidate.id for candidate in self.ranking_request.candidates)
        expected_nodes = {(self.cve_id, "vulnerability")} | {(name, "strategy") for name in names}
        expected_edges = {(self.cve_id, name) for name in names}
        if len(names) > 1:
            expected_edges |= set(zip(names, names[1:] + names[:1], strict=True))
        actual_edges = {(edge.source, edge.target) for edge in graph.edges}
        if (
            {(node.id, node.type) for node in graph.nodes} != expected_nodes
            or actual_edges != expected_edges
            or len(actual_edges) != len(graph.edges)
            or any(candidate.name != candidate.id for candidate in self.ranking_request.candidates)
        ):
            raise ValueError("Generator topology differs from bottalico-directed-ring-v1")
        if {(e.source, e.target) for e in self.edge_sources} != {
            (e.source, e.target) for e in graph.edges
        } or len(self.edge_sources) != len(graph.edges):
            raise ValueError("Every native edge requires exactly one source annotation")
        for edge in self.edge_sources:
            expected = (
                "kg_remediation" if edge.source == self.cve_id else "generator_comparison_ring"
            )
            if edge.origin != expected:
                raise ValueError("Edge source contradicts its topology")
        return self


class PreparationArtifact(WireModel):
    contract: Literal["canonical-preparation-v1"] = "canonical-preparation-v1"
    run_id: Identifier
    asset_id: Identifier
    request_sha256: SHA256
    input_digests: dict[InputName, SHA256]
    knowledge_snapshot_id: Text
    source_ontology_sha256: SHA256
    generator_manifest_sha256: SHA256
    observed_assets_sha256: SHA256
    aln_ontology_sha256: SHA256
    bindings: list[CandidateBinding]
    graphs: list[CanonicalGraph] = Field(min_length=1)
    backend_weights: Literal["not_computed"] = "not_computed"
    assessment_origin: Literal["mas_findings_with_explicit_operator_kg_bindings"] = (
        "mas_findings_with_explicit_operator_kg_bindings"
    )
    deployment_verified: Literal[False] = False

    @model_validator(mode="after")
    def coverage(self):
        require_unique([g.cve_id for g in self.graphs], "canonical CVE graphs")
        require_unique(
            [f"{b.cve_id}:{b.strategy_id}" for b in self.bindings], "CVE/candidate bindings"
        )
        require_unique(
            [f"{b.cve_id}:{b.ontology_individual}" for b in self.bindings], "CVE/KG bindings"
        )
        if set(self.input_digests) != {
            "runtime_evidence",
            "vulnerability_report",
            "candidate_strategies",
        }:
            raise ValueError("All three MAS artifact digests are required")
        if {g.cve_id for g in self.graphs} != {b.cve_id for b in self.bindings}:
            raise ValueError("Canonical graphs must cover all bindings")
        for graph in self.graphs:
            request = graph.ranking_request
            expected = {b.ontology_individual for b in self.bindings if b.cve_id == graph.cve_id}
            if {c.id for c in request.candidates} != expected:
                raise ValueError("Native candidate IDs differ from their explicit KG bindings")
            if request.knowledge_snapshot_id != self.knowledge_snapshot_id:
                raise ValueError("Native request snapshot differs from preparation")
        return self
