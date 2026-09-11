# Esiti della validazione e decisione finale. La selezione deve essere sostenuta
# dai tool: il modello non può dichiarare accettata una strategia rifiutata.
# Questi controlli interni si sommano ai confronti fra artefatti in ArtifactSession.
from typing import Literal

from pydantic import StrictBool, model_validator

from .argumentation import RankedStrategy
from .base import Identifier, Message, Text


class SemanticValidationResult(Message):
    # Un tentativo riguarda una sola strategia. missing_requirements elenca capacità
    # assenti; conflicts elenca incompatibilità rilevate. backend identifica il tool.
    strategy_id: Identifier
    valid: StrictBool
    status: Literal["accepted", "rejected"]
    missing_requirements: list[Text]
    conflicts: list[Text]
    explanation: Text
    backend: str

    @model_validator(mode="after")
    def check_status(self):
        # valid e status esprimono lo stesso esito e devono concordare. Un risultato
        # accettato non può contemporaneamente dichiarare conflitti o requisiti mancanti.
        if self.valid != (self.status == "accepted"):
            raise ValueError("Validation status disagrees with valid")
        if self.valid and (self.missing_requirements or self.conflicts):
            raise ValueError("Accepted validation cannot contain conflicts or missing requirements")
        return self


class SemanticValidationReport(Message):
    # Conserva tutti i tentativi eseguiti, anche i rifiuti che spiegano il fallback.
    # L'ordine e l'arresto al primo successo sono imposti dalla sessione, non qui.
    validations: list[SemanticValidationResult]


class FinalDecision(Message):
    # selected: proposta accettata; no_valid_strategy: tutte le alternative rifiutate;
    # insufficient_evidence: lookup non coperto. «Selected» non esegue la contromisura.
    status: Literal["selected", "no_valid_strategy", "insufficient_evidence"]
    selected_strategy_id: Identifier | None
    ranking: list[RankedStrategy]
    semantic_validation: SemanticValidationResult | None
    # Classifica completa e validazione della sola strategia scelta sono copiate
    # dai tool. L'elenco di tutti i tentativi rimane in semantic_validation.json.
    evidence_ids: list[Identifier]
    # Questi ID provengono dall'evidenza originale, non da un riepilogo del report KG.
    explanation: Text

    @model_validator(mode="after")
    def check_selection(self):
        # La verifica locale richiede una validazione accettata per lo stesso ID
        # presente in classifica. La sessione controlla in più che sia il primo
        # candidato accettato in ordine e che tutti gli input originali esistano.
        if self.status == "selected":
            if not self.semantic_validation or not self.semantic_validation.valid:
                raise ValueError("Selection requires accepted semantic validation")
            if self.semantic_validation.strategy_id != self.selected_strategy_id:
                raise ValueError("Selection and validation strategy IDs differ")
            if self.selected_strategy_id not in [r.strategy_id for r in self.ranking]:
                raise ValueError("Selected strategy is absent from ranking")
        elif self.selected_strategy_id is not None or self.semantic_validation is not None:
            raise ValueError("Unselected decisions must not include a selected strategy")
        return self
