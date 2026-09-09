from pydantic import Field, StrictBool, model_validator

from .base import Identifier, Message, Text, require_unique


class StaticTelemetry(Message):
    service_name: Identifier
    package_name: Text
    package_version: Text
    endpoint_exposed: StrictBool
    deserialization_observed: StrictBool
    available_capabilities: list[Text] = Field(default_factory=list)
    prohibited_actions: list[Text] = Field(default_factory=list)


class SoftwareObservation(Message):
    package: Text
    version: Text
    evidence_id: Identifier


class RuntimeEvidence(Message):
    service_name: Identifier
    software: list[SoftwareObservation] = Field(min_length=1)
    endpoint_exposed: StrictBool
    deserialization_observed: StrictBool
    observations: list[Text]

    @model_validator(mode="after")
    def unique_evidence(self):
        require_unique([s.evidence_id for s in self.software], "evidence IDs")
        return self
