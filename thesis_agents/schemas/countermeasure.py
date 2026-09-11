# Contratti delle strategie e del contesto passato al validatore semantico.
# Le candidate appartengono al layer generativo CAMEL; non contengono ancora
# un ranking autorevole né una decisione sulla loro validità semantica.
from typing import Literal

from pydantic import Field, model_validator

from .base import Identifier, Message, Text, UnitScore, require_unique
from .telemetry import RuntimeEvidence
from .vulnerability import VulnerabilityReport

# Vocabolario chiuso del primo MVP: il mock associa requisiti a queste categorie.
# È distinto dalla descrizione libera, che specifica l'azione proposta nel caso.
Action = Literal["upgrade", "isolate", "block_deployment", "monitor"]


class CountermeasureCandidate(Message):
    # ID stabile per collegare proposta, argomenti, ranking, validazione e decisione.
    id: Identifier
    action: Action
    description: Text
    addressed_vulnerabilities: list[Text] = Field(min_length=1)
    # L'appartenenza delle CVE al report viene controllata dalla sessione: richiede
    # un confronto fra artefatti, che questo modello isolato non può effettuare.
    security_benefit: UnitScore
    operational_impact: UnitScore
    # Sono stime della proposta (o numeri della fixture), non il risultato del ranking.
    prerequisites: list[Text]
    constraints: list[Text]
    # prerequisites contiene nomi di capacità confrontabili automaticamente;
    # constraints contiene caveat testuali che il mock non interpreta semanticamente.
    rationale: Text


class CandidateStrategies(Message):
    # Fino a otto alternative per mantenere piccolo il caso. Il set vuoto è lecito
    # nello schema; la sessione lo consente solo quando manca un finding utilizzabile.
    strategies: list[CountermeasureCandidate] = Field(max_length=8)

    @model_validator(mode="after")
    def unique_strategies(self):
        # Un ID duplicato renderebbe ambigua la scelta effettuata dallo StrategicAgent.
        require_unique([s.id for s in self.strategies], "strategy IDs")
        return self


class DecisionContext(Message):
    # Contesto del singolo controllo semantico, non un nuovo artefatto sostitutivo.
    # La strategia viene passata al tool come argomento separato. Evidence e report
    # restano due modelli distinti, accompagnati dalle capacità e policy dell'input.
    evidence: RuntimeEvidence
    vulnerabilities: VulnerabilityReport
    available_capabilities: list[Text]
    prohibited_actions: list[Text]
