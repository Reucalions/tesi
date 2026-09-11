# Contratti dei backend esterni al ragionamento generativo degli agenti.
# Protocol definisce una compatibilità strutturale: un adapter può soddisfare
# l'interfaccia implementando il metodo richiesto, senza ereditarne la classe.
# Le firme sono indicazioni di tipo, non implementazioni né controlli runtime;
# ArtifactSession applica i controlli sui risultati ricevuti dai backend.
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
    # Ingresso: un'osservazione software già pubblicata, con riferimento all'evidenza.
    # Uscita: finding correlati oppure indicazione che il backend non copre il caso.
    def lookup_vulnerabilities(self, software: SoftwareObservation) -> LookupResult: ...


class RankingTool(Protocol):
    # Riceve il grafo completo e restituisce un ordine deterministico di strategie.
    # Un futuro adapter può incapsulare più chiamate MCP dietro questa singola firma.
    def rank_graph(self, graph: ArgumentationGraph) -> RankingResult: ...


class SemanticTool(Protocol):
    # Controlla una candidata alla volta usando evidence, report e policy del caso.
    # Non sceglie il candidato successivo: è il flusso strategico a gestire il fallback.
    def validate_countermeasure(
        self, strategy: CountermeasureCandidate, context: DecisionContext
    ) -> SemanticValidationResult: ...


class ProvenanceTool(Protocol):
    # Persiste il record già costruito e restituisce una ricevuta. Nel mock la
    # ricevuta conferma una scrittura locale, non una transazione su un ledger.
    def record_provenance(self, record: ProvenanceRecord) -> dict: ...
