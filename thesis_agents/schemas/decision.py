from typing import Literal

from pydantic import StrictBool, model_validator

from .argumentation import RankedStrategy
from .base import Identifier, Message, Text


class SemanticValidationResult(Message):
    strategy_id: Identifier
    valid: StrictBool
    status: Literal["accepted", "rejected"]
    missing_requirements: list[Text]
    conflicts: list[Text]
    explanation: Text
    backend: str

    @model_validator(mode="after")
    def check_status(self):
        if self.valid != (self.status == "accepted"):
            raise ValueError("Validation status disagrees with valid")
        if self.valid and (self.missing_requirements or self.conflicts):
            raise ValueError("Accepted validation cannot contain conflicts or missing requirements")
        return self


class SemanticValidationReport(Message):
    validations: list[SemanticValidationResult]


class FinalDecision(Message):
    status: Literal["selected", "no_valid_strategy", "insufficient_evidence"]
    selected_strategy_id: Identifier | None
    ranking: list[RankedStrategy]
    semantic_validation: SemanticValidationResult | None
    evidence_ids: list[Identifier]
    explanation: Text

    @model_validator(mode="after")
    def check_selection(self):
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
