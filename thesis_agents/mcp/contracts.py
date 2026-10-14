"""Contratti pubblici MCP: il formato di dominio resta quello Pydantic del progetto."""

from typing import Annotated, Literal

from pydantic import Field, StrictBool, field_validator

from thesis_agents.mcp.v1_domain import DecisionContext, LookupResult, legacy_payload
from thesis_agents.schemas import (
    ArgumentationGraph,
    CountermeasureCandidate,
    ProvenanceRecord,
    RankingResult,
    SemanticValidationResult,
    SoftwareObservation,
)
from thesis_agents.schemas.base import Identifier, Message, Text

LOOKUP_TOOL = "lookup_vulnerabilities"
LOOKUP_CONTRACT = "vulnerability-lookup-v1"
RANKING_TOOL = "rank_graph"
RANKING_CONTRACT = "argumentation-ranking-v1"
SEMANTIC_TOOL = "validate_countermeasure"
SEMANTIC_CONTRACT = "semantic-validation-v1"
PROVENANCE_TOOL = "record_provenance"
PROVENANCE_CONTRACT = "provenance-record-v1"
SHA256 = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]


class LookupRequest(Message):
    software: SoftwareObservation


class LookupResponse(Message):
    # Il trasporto è reale anche se il servizio dichiara un backend mock.
    contract: Literal["vulnerability-lookup-v1"]
    backend_kind: Literal["mock", "real"]
    backend: Text
    result: LookupResult

    @field_validator("result", mode="before")
    @classmethod
    def preserve_v1(cls, value):
        return legacy_payload(value)


class RankingRequest(Message):
    graph: ArgumentationGraph


class SemanticRequest(Message):
    strategy: CountermeasureCandidate
    context: DecisionContext

    @field_validator("context", mode="before")
    @classmethod
    def preserve_v1(cls, value):
        return legacy_payload(value)


class ProvenanceRequest(Message):
    record: ProvenanceRecord


class RemoteResponse(Message):
    backend_kind: Literal["mock", "real"]
    backend: Text
    # Lega la risposta all'intero input, incluse policy e pesi, non soltanto agli ID.
    # È una dichiarazione del servizio verificata dal client, non una firma/prova.
    request_sha256: SHA256


class RankingResponse(RemoteResponse):
    contract: Literal["argumentation-ranking-v1"]
    result: RankingResult


class SemanticResponse(RemoteResponse):
    contract: Literal["semantic-validation-v1"]
    result: SemanticValidationResult


class ProvenanceReceipt(Message):
    run_id: Identifier
    stored: StrictBool
    record_sha256: SHA256
    receipt_id: Text
    backend: Text


class ProvenanceResponse(RemoteResponse):
    contract: Literal["provenance-record-v1"]
    result: ProvenanceReceipt
