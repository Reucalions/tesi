"""Contratto additivo v2: copertura lessicale esplicita, nessuna applicabilità CVE."""

from typing import Annotated, Literal

from pydantic import Field, StrictBool, model_validator

from .cti_contracts import (
    SHA256,
    AssessmentResponse,
    Count,
    DatasetReference,
    MatchingResult,
    Message,
    SoftwareQuery,
    Text,
)
from .identity_contracts import IdentityCandidate, IdentityEvidence, IdentityRequest

TOOL = "resolve_software_identity"
CONTRACT = "cti-identity-resolution-v2"


class SearchCoverage(Message):
    scope: Literal["baseline-normalized-product-exact-and-token"]
    indexed_identities: Count
    candidate_bound: Annotated[int, Field(ge=1, strict=True)]
    token_bound: Annotated[int, Field(ge=1, strict=True)]
    generated_candidates: Count
    rejected_by_matcher: Count
    returned_candidates: Count
    complete: StrictBool
    vector_search: Literal[False] = False

    @model_validator(mode="after")
    def consistent_counts(self):
        if (
            self.generated_candidates > self.indexed_identities
            or self.generated_candidates != self.rejected_by_matcher + self.returned_candidates
        ):
            raise ValueError("Search candidate counts are inconsistent")
        expected = (
            self.candidate_bound > self.indexed_identities
            and self.token_bound > self.indexed_identities
            and self.returned_candidates < self.candidate_bound
        )
        if self.complete != expected:
            raise ValueError("Search completeness differs from declared bounds")
        return self


class IdentitySearch(Message):
    software: SoftwareQuery
    dataset: DatasetReference
    engine_sha256: dict[str, SHA256] = Field(min_length=1)
    search_sha256: SHA256
    coverage: SearchCoverage
    matching: MatchingResult

    @model_validator(mode="after")
    def consistent_search(self):
        asset = self.matching.asset
        if (asset.product, asset.version, asset.vendor) != (
            self.software.product,
            self.software.version,
            self.software.vendor,
        ):
            raise ValueError("Search asset differs from the normalized query")
        ids = [m.canonical_id for m in self.matching.matches]
        if len(ids) != len(set(ids)) or len(ids) != self.coverage.returned_candidates:
            raise ValueError("Search must preserve every unique returned candidate")
        return self


class IdentityResolution(Message):
    contract: Literal["cti-identity-resolution-v2"] = CONTRACT
    backend_kind: Literal["real", "mock"]
    request_sha256: SHA256
    evidence: IdentityEvidence
    rule_id: Literal["apache-recorded-identity-v2"] = "apache-recorded-identity-v2"
    rule_sha256: SHA256
    resolver_sha256: SHA256
    reviewed_dataset_sha256: SHA256
    status: Literal["resolved", "ambiguous", "no_match", "insufficient_evidence", "unreviewed"]
    normalized_query: SoftwareQuery | None
    group_id: Literal["apache:http_server"] | None
    selected_identity_ids: list[Text]
    candidates: list[IdentityCandidate]
    # V1 top-20 lookup remains intact, separate from full lexical identity discovery.
    upstream_assessment: AssessmentResponse | None
    search: IdentitySearch | None
    package_applicability: Literal["not_assessed"] = "not_assessed"
    limitations: list[Text] = Field(min_length=1)

    @model_validator(mode="after")
    def consistent_resolution(self):
        if self.search is None:
            if (
                self.status != "insufficient_evidence"
                or self.candidates
                or self.upstream_assessment is not None
                or self.normalized_query is not None
                or self.group_id is not None
                or self.selected_identity_ids
            ):
                raise ValueError("Unsupported context must not perform or select a lookup")
            return self
        raw = self.upstream_assessment
        query = self.normalized_query
        if raw is None or query is None:
            raise ValueError("Search and original upstream lookup must remain together")
        original = self.evidence.software
        if (query.product, query.version, query.vendor, query.evidence_id) != (
            "Apache HTTP Server",
            original.version,
            None,
            original.evidence_id,
        ):
            raise ValueError("Normalization may change only the observed product name")
        if (
            raw.software != query
            or self.search.software != query
            or raw.backend_kind != self.backend_kind
            or raw.dataset != self.search.dataset
            or raw.engine_sha256 != self.search.engine_sha256
            or raw.matching.query != self.search.matching.query
        ):
            raise ValueError("Search and upstream lookup must use the same query and snapshot")
        ids = [c.canonical_id for c in self.candidates]
        matches = self.search.matching.matches
        full = {m.canonical_id: m for m in matches}
        for match in raw.matching.matches:
            discovered = full.get(match.canonical_id)
            fields = {
                "canonical_id",
                "vendor",
                "product",
                "normalized_vendor",
                "normalized_product",
                "confidence",
                "score",
                "affected_count",
            }
            entries = {
                "affected_product_id",
                "cve_id",
                "affected_iri",
                "json_path",
                "vendor",
                "product",
            }
            if (
                discovered is None
                or match.model_dump(include=fields) != discovered.model_dump(include=fields)
                or not set(match.evidence) <= set(discovered.evidence)
                or not (set(discovered.evidence) - set(match.evidence)) <= {"sqlite_token"}
                or [e.model_dump(include=entries) for e in match.affected_entries]
                != [e.model_dump(include=entries) for e in discovered.affected_entries]
            ):
                raise ValueError("Full search changed an original upstream candidate")
        if ids != [m.canonical_id for m in matches]:
            raise ValueError("Every search candidate must remain visible in order")
        for candidate, match in zip(self.candidates, matches, strict=True):
            if candidate.entry_count != len(match.affected_entries) or candidate.cve_ids != [
                e.cve_id for e in match.affected_entries
            ]:
                raise ValueError("Candidate CVEs differ from the search entries")
            if candidate.disposition == "equivalent" and not candidate.references:
                raise ValueError("Reviewed equivalence requires source references")
        equivalents = [c.canonical_id for c in self.candidates if c.disposition == "equivalent"]
        if raw.dataset.sha256 != self.reviewed_dataset_sha256:
            expected = "unreviewed"
            if any(c.disposition != "unresolved" for c in self.candidates):
                raise ValueError("An unreviewed dataset cannot classify identities")
        elif not self.search.coverage.complete or any(
            c.disposition == "unresolved" for c in self.candidates
        ):
            expected = "ambiguous"
        else:
            expected = "resolved" if equivalents else "no_match"
        if self.status != expected:
            raise ValueError("Identity status differs from coverage and classifications")
        resolved = expected == "resolved"
        if self.selected_identity_ids != (equivalents if resolved else []) or self.group_id != (
            "apache:http_server" if resolved else None
        ):
            raise ValueError("Only a complete reviewed resolution may select identities")
        return self


__all__ = [
    "CONTRACT",
    "TOOL",
    "IdentityRequest",
    "IdentityResolution",
    "IdentitySearch",
    "SearchCoverage",
]
