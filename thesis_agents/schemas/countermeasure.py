from typing import Literal

from pydantic import Field, model_validator

from .base import Identifier, Message, Text, UnitScore, require_unique
from .telemetry import RuntimeEvidence
from .vulnerability import VulnerabilityReport

Action = Literal["upgrade", "isolate", "block_deployment", "monitor"]


class CountermeasureCandidate(Message):
    id: Identifier
    action: Action
    description: Text
    addressed_vulnerabilities: list[Text] = Field(min_length=1)
    security_benefit: UnitScore
    operational_impact: UnitScore
    prerequisites: list[Text]
    constraints: list[Text]
    rationale: Text


class CandidateStrategies(Message):
    strategies: list[CountermeasureCandidate] = Field(max_length=8)

    @model_validator(mode="after")
    def unique_strategies(self):
        require_unique([s.id for s in self.strategies], "strategy IDs")
        return self


class DecisionContext(Message):
    evidence: RuntimeEvidence
    vulnerabilities: VulnerabilityReport
    available_capabilities: list[Text]
    prohibited_actions: list[Text]
