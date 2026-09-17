# Esiti della validazione e decisione finale. La selezione deve essere sostenuta
# dai tool: il modello non può dichiarare accettata una strategia rifiutata.
# Questi controlli interni si sommano ai confronti fra artefatti in ArtifactSession.
from typing import Literal

from pydantic import Field, StrictBool, model_validator

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


class ExplanationSource(Message):
    # JSON Pointer verso un campo dell'artefatto, non verso un riepilogo LLM.
    artifact: Literal[
        "input",
        "runtime_evidence",
        "vulnerability_report",
        "candidate_strategies",
        "ranking",
        "semantic_validation",
    ]
    pointer: str = Field(pattern=r"^(/[^/~]*(~[01][^/~]*)*)*$")
    producer: Text


class ExplanationClaim(Message):
    category: Literal["reported_fact", "estimate", "decision", "limitation"]
    text: Text
    sources: list[ExplanationSource] = Field(min_length=1)


class AgentCommentary(Message):
    # Conserva il testo originale senza attribuirgli una verifica semantica.
    text: Text
    verification: Literal["unverified"] = "unverified"


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
    # I JSON storici restano leggibili, ma il testo legacy non diventa verificato.
    explanation_method: Literal["legacy-unverified", "artifact-derived-v1"] = "legacy-unverified"
    explanation_claims: list[ExplanationClaim] = Field(default_factory=list)
    agent_commentary: AgentCommentary | None = None

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
        if self.explanation_method == "artifact-derived-v1":
            if not self.explanation_claims or self.agent_commentary is None:
                raise ValueError(
                    "Derived explanations require claims and separate agent commentary"
                )
            if self.explanation != "\n\n".join(c.text for c in self.explanation_claims):
                raise ValueError("Explanation text must match its source-linked claims")
        elif self.explanation_claims or self.agent_commentary is not None:
            raise ValueError("Legacy explanations cannot claim verified attribution")
        return self
