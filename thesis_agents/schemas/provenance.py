from typing import Literal

from .base import Identifier, Message, Text


class ProvenanceEntity(Message):
    id: Identifier
    filename: Text
    sha256: Text


class ProvenanceActivity(Message):
    id: Identifier
    agent: Text
    used: list[Identifier]
    generated: list[Identifier]


class ProvenanceRecord(Message):
    run_id: Identifier
    mode: Literal["camel", "fixtures"]
    backend: Literal["local-provenance-mock-v1"] = "local-provenance-mock-v1"
    model: str | None
    created_at: Text
    entities: list[ProvenanceEntity]
    activities: list[ProvenanceActivity]
    agents: list[Text]
