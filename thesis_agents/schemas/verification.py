"""Richieste di evidenza: proposte di verifica, senza esecuzione o esiti inventati."""

from typing import Literal

from pydantic import Field, model_validator

from .base import Identifier, Message, Text, require_unique
from .ubuntu import CVE, SHA256


class VerificationRequest(Message):
    id: Identifier
    kind: Literal[
        "historical_runtime_state", "runtime_conditions", "ubuntu_status", "upgrade_compatibility"
    ]
    status: Literal["pending"] = "pending"
    purpose: Literal["evidence_collection_only"] = "evidence_collection_only"
    cve_ids: list[CVE] = Field(min_length=1)
    required_evidence: list[Text] = Field(min_length=1)
    source_artifact: Literal["vulnerability_report"] = "vulnerability_report"
    source_pointers: list[Text] = Field(min_length=1)

    @model_validator(mode="after")
    def unique_cves(self):
        require_unique(self.cve_ids, "verification CVE IDs")
        if self.cve_ids != sorted(self.cve_ids):
            raise ValueError("Verification CVEs must be sorted")
        return self


class PackageVerificationContext(Message):
    contract: Literal["ubuntu-countermeasure-context-v1"] = "ubuntu-countermeasure-context-v1"
    asset_id: Identifier
    runtime_evidence_id: Identifier
    runtime_evidence_sha256: SHA256
    vulnerability_report_sha256: SHA256
    package_response_sha256: SHA256
    package_response_file: Literal["ubuntu_package_assessment.json"] = (
        "ubuntu_package_assessment.json"
    )
    verification_requests: list[VerificationRequest] = Field(max_length=4)
    limitations: list[Text] = Field(min_length=1)

    @model_validator(mode="after")
    def unique_requests(self):
        require_unique([r.id for r in self.verification_requests], "verification request IDs")
        require_unique([r.kind for r in self.verification_requests], "verification request kinds")
        return self
