"""Contratto del resolver remoto: identità upstream distinta dall'applicabilità CVE.

Copia del solo contratto pubblico del backend, senza import del suo motore.
"""

from typing import Annotated, Literal

from pydantic import AwareDatetime, Field, model_validator

from .cti_contracts import SHA256, AssessmentResponse, Message, SoftwareQuery, Text

TOOL = "resolve_software_identity"
CONTRACT = "cti-identity-resolution-v1"


class IdentityEvidence(Message):
    software: SoftwareQuery
    identity_basis: Text
    service: Text
    host: Text
    instance_basis: Text
    inventory_package: Text
    inventory_version: Text
    inventory_origin: Text
    facts_collected_at: AwareDatetime
    telemetry_snapshot_sha256: SHA256
    export_sha256: SHA256
    facts_sha256: SHA256
    record_sha256: SHA256
    original_log_sha256: SHA256
    record_pointer: str = Field(pattern=r"^/resourceLogs/\d+/scopeLogs/\d+/logRecords/\d+$")


class IdentityRequest(Message):
    evidence: IdentityEvidence


class IdentityCandidate(Message):
    canonical_id: Text
    disposition: Literal["equivalent", "excluded", "unresolved"]
    reason: Text
    entry_count: Annotated[int, Field(ge=0, strict=True)]
    cve_ids: list[Text]
    references: list[Text]


class IdentityResolution(Message):
    contract: Literal["cti-identity-resolution-v1"] = CONTRACT
    backend_kind: Literal["real", "mock"]
    request_sha256: SHA256
    evidence: IdentityEvidence
    rule_id: Literal["apache-recorded-identity-v1"] = "apache-recorded-identity-v1"
    rule_sha256: SHA256
    resolver_sha256: SHA256
    status: Literal["resolved", "ambiguous", "no_match", "insufficient_evidence", "unreviewed"]
    normalized_query: SoftwareQuery | None
    # Un gruppo può conservare più identità lessicali del medesimo prodotto.
    group_id: Literal["apache:http_server"] | None
    selected_identity_ids: list[Text]
    candidates: list[IdentityCandidate]
    upstream_assessment: AssessmentResponse | None
    package_applicability: Literal["not_assessed"] = "not_assessed"
    limitations: list[Text] = Field(min_length=1)

    @model_validator(mode="after")
    def consistent_resolution(self):
        resolved = self.status == "resolved"
        ids = [c.canonical_id for c in self.candidates]
        equivalents = [c.canonical_id for c in self.candidates if c.disposition == "equivalent"]
        if len(ids) != len(set(ids)) or self.selected_identity_ids != (
            equivalents if resolved else []
        ):
            raise ValueError("Identity selection must preserve classified candidates")
        if resolved != (self.group_id is not None) or (
            resolved
            and (not equivalents or any(c.disposition == "unresolved" for c in self.candidates))
        ):
            raise ValueError("Unresolved candidates cannot form a resolved group")
        if (self.normalized_query is None) != (self.upstream_assessment is None):
            raise ValueError("Normalized lookup and response must remain together")
        if self.upstream_assessment is None:
            if self.candidates or self.status != "insufficient_evidence":
                raise ValueError("Only insufficient evidence may omit the lookup")
        else:
            response = self.upstream_assessment
            if self.status == "insufficient_evidence":
                raise ValueError("Insufficient context must not trigger a normalized lookup")
            if resolved and len(ids) >= response.policy.match_limit:
                raise ValueError("A saturated candidate list cannot resolve the identity")
            if self.status == "no_match" and any(
                c.disposition != "excluded" for c in self.candidates
            ):
                raise ValueError("No match cannot hide equivalent or unresolved candidates")
            if (
                response.software != self.normalized_query
                or response.backend_kind != self.backend_kind
            ):
                raise ValueError("Normalized query/backend does not match the lookup")
            if ids != [m.canonical_id for m in response.matching.matches]:
                raise ValueError("Every returned identity must remain visible in order")
            original = self.evidence.software
            query = self.normalized_query
            if (query.product, query.version, query.vendor, query.evidence_id) != (
                "Apache HTTP Server",
                original.version,
                None,
                original.evidence_id,
            ):
                raise ValueError("Identity normalization may change only the product name")
            for candidate, match in zip(self.candidates, response.matching.matches, strict=True):
                if candidate.entry_count != len(match.affected_entries) or candidate.cve_ids != [
                    e.cve_id for e in match.affected_entries
                ]:
                    raise ValueError("Candidate sources must match the original lookup")
        return self
