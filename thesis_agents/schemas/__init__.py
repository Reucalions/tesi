# Punto di importazione pubblico dei contratti più usati. I consumatori possono
# importare da thesis_agents.schemas senza conoscere il file di ogni modello.
# Non viene creato alcun oggetto di dominio: qui si riesportano solo definizioni.
from .argumentation import ArgumentationGraph, RankingResult
from .countermeasure import CandidateStrategies, CountermeasureCandidate, DecisionContext
from .decision import FinalDecision, SemanticValidationReport, SemanticValidationResult
from .provenance import ProvenanceRecord
from .telemetry import RuntimeEvidence, SoftwareObservation, StaticTelemetry
from .vulnerability import LookupResult, VulnerabilityFinding, VulnerabilityReport

# Elenco dei nomi pubblici per «from ... import *» e per rendere esplicita l'API.
# I modelli ausiliari non elencati restano importabili dal rispettivo modulo.
__all__ = [
    "ArgumentationGraph",
    "RankingResult",
    "CandidateStrategies",
    "CountermeasureCandidate",
    "DecisionContext",
    "FinalDecision",
    "SemanticValidationReport",
    "SemanticValidationResult",
    "ProvenanceRecord",
    "RuntimeEvidence",
    "SoftwareObservation",
    "StaticTelemetry",
    "LookupResult",
    "VulnerabilityFinding",
    "VulnerabilityReport",
]
