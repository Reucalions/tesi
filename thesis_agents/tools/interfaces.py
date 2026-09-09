from typing import Protocol

from thesis_agents.schemas import (
    ArgumentationGraph,
    CountermeasureCandidate,
    DecisionContext,
    LookupResult,
    ProvenanceRecord,
    RankingResult,
    SemanticValidationResult,
    SoftwareObservation,
)


class VulnerabilityTool(Protocol):
    def lookup_vulnerabilities(self, software: SoftwareObservation) -> LookupResult: ...


class RankingTool(Protocol):
    def rank_graph(self, graph: ArgumentationGraph) -> RankingResult: ...


class SemanticTool(Protocol):
    def validate_countermeasure(
        self, strategy: CountermeasureCandidate, context: DecisionContext
    ) -> SemanticValidationResult: ...


class ProvenanceTool(Protocol):
    def record_provenance(self, record: ProvenanceRecord) -> dict: ...
