"""Lettura verificabile dell'archivio di provenienza, distinta dal ledger."""

from typing import Literal

from pydantic import field_validator

from thesis_agents.mcp.contracts import SHA256
from thesis_agents.schemas import ProvenanceRecord
from thesis_agents.schemas.base import Identifier, Message

READ_TOOL = "read_provenance"


class ReadProvenanceRequest(Message):
    run_id: Identifier

    @field_validator("run_id")
    @classmethod
    def safe_segment(cls, value):
        if value in (".", ".."):
            raise ValueError("Run ID must name a run, not a directory")
        return value


class ReadProvenanceResponse(Message):
    contract: Literal["artifact-provenance-read-v1"] = "artifact-provenance-read-v1"
    backend_kind: Literal["real"] = "real"
    backend: Literal["artifact-jsonld-store-v1"] = "artifact-jsonld-store-v1"
    request_sha256: SHA256
    record: ProvenanceRecord
    record_sha256: SHA256
    jsonld: dict
    jsonld_sha256: SHA256
    storage_kind: Literal["artifact-files"] = "artifact-files"
    ledger_status: Literal["not_submitted"] = "not_submitted"
