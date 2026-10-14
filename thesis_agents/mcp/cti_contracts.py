"""Public cve2owl-assessment-v1 wire contract, independent of CAMEL and tesi.

Clients may copy this contract module, but never import the backend engine.
Scores and statuses retain the baseline's meaning; no CVSS is fabricated.
"""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool

TOOL = "assess_software"
CONTRACT = "cve2owl-assessment-v1"
Text = Annotated[str, Field(min_length=1)]
Count = Annotated[int, Field(ge=0, strict=True)]
SHA256 = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
Confidence = Literal["high", "medium", "needs_review", "no_match"]
Status = Literal["vulnerable", "not_vulnerable", "unknown", "not_evaluable", "skipped"]


class Message(BaseModel):
    model_config = ConfigDict(extra="forbid")


class SoftwareQuery(Message):
    product: Annotated[str, Field(min_length=1, max_length=256, pattern=r"\S")]
    version: Annotated[str, Field(min_length=1, max_length=256, pattern=r"\S")] | None = None
    vendor: Annotated[str, Field(min_length=1, max_length=256, pattern=r"\S")] | None = None
    evidence_id: Annotated[str, Field(min_length=1, max_length=128, pattern=r"\S")]


class AssessmentRequest(Message):
    software: SoftwareQuery


class DatasetReference(Message):
    id: Text
    sha256: SHA256
    kind: Literal["real", "fixture"]


class EvaluationPolicy(Message):
    match_limit: Annotated[int, Field(ge=1, le=20)]
    confidence_levels: list[Literal["high"]] = Field(min_length=1, max_length=1)
    vector_search: Literal[False] = False


class ProductAsset(Message):
    product: Text
    version: str | None = None
    vendor: str | None = None
    asset_type: str | None = None


class MatchingQuery(Message):
    product_terms: list[str]
    normalized_product_terms: list[str]
    vendor: str | None
    normalized_vendor: str


class VersionChange(Message):
    affected_version_change_id: Count
    json_path: str
    at: str | None
    status: str | None


class VersionRule(Message):
    affected_version_id: Count
    json_path: str
    version_iri: str | None
    version: str | None
    status: str | None
    version_type: str | None
    less_than: str | None
    less_than_or_equal: str | None
    changes: list[VersionChange]
    evaluated: StrictBool
    matched_asset_version: StrictBool
    vulnerability_status: Status
    reason: Text


class AffectedEntry(Message):
    affected_product_id: Count
    cve_id: Annotated[str, Field(pattern=r"^CVE-\d{4}-\d{4,}$")]
    affected_iri: str
    json_path: str
    vendor: str
    product: str
    # Raw matching entries have no assessment yet; None is not a negative result.
    vulnerability_status: Status | None = None
    vulnerability_reason: str | None = None
    version_rules: list[VersionRule] = Field(default_factory=list)
    cpes: list[str] = Field(default_factory=list)


class VersionEvaluation(Message):
    eligible: StrictBool
    confidence_required: list[str]
    asset_version_parseable: StrictBool | None
    comparable_version: str | None
    cve_counts: dict[str, Count]


class ProductMatch(Message):
    canonical_id: Text
    vendor: str
    product: str
    normalized_vendor: str
    normalized_product: str
    affected_count: Count
    confidence: Confidence
    # The existing heuristic score is NOT a probability and need not be <= 1.
    score: Annotated[float, Field(ge=0, allow_inf_nan=False)]
    evidence: list[str]
    affected_entries: list[AffectedEntry]
    vulnerability_status: Status | None = None
    vulnerability_reason: str | None = None
    evaluated_asset_version: str | None = None
    version_evaluation: VersionEvaluation | None = None


class MatchingResult(Message):
    asset: ProductAsset
    query: MatchingQuery
    status: Literal["matched", "no_match", "needs_review"]
    matches: list[ProductMatch]


class AssessmentSummary(Message):
    confidence_required: list[str]
    assets_total: Count
    assets_with_assessments: Count
    matches_total: Count
    matches_evaluated: Count
    matches_skipped_by_confidence: Count
    vulnerability_status_counts: dict[str, Count]


class AssessmentReport(Message):
    assessment_summary: AssessmentSummary
    results: list[MatchingResult]


class AssessmentResponse(Message):
    contract: Literal["cve2owl-assessment-v1"]
    backend_kind: Literal["mock", "real"]
    backend: Literal["cve2owl-symbolic-v1"]
    request_sha256: SHA256
    software: SoftwareQuery
    dataset: DatasetReference
    engine_sha256: dict[str, SHA256]
    policy: EvaluationPolicy
    # Preserve all returned candidates, including low-confidence or ambiguous ones.
    # The report assesses only high-confidence matches under the policy above.
    matching: MatchingResult
    assessment: AssessmentReport
