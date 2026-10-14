"""Sintesi autorevole della correlazione remota; la risposta completa resta su file.

La copertura riguarda solo le regole dei candidati restituiti. Non certifica
completezza del dataset, correttezza delle fonti o assenza globale di vulnerabilità.
"""

from typing import Annotated, Literal

from pydantic import Field

from .base import Message, Text
from .telemetry import SoftwareObservation

SHA256 = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
LookupStatus = Literal[
    "matched", "unsupported", "ambiguous", "no_match", "not_evaluable", "no_findings"
]


class CTIIdentity(Message):
    canonical_id: Text
    product: str
    vendor: str
    confidence: Literal["high", "medium", "needs_review", "no_match"]
    score: Annotated[float, Field(ge=0, allow_inf_nan=False)]


class CTICVEAssessment(Message):
    canonical_id: Text
    cve_id: Text
    affected_product_id: int
    affected_iri: str
    json_path: str
    status: Literal["vulnerable", "not_vulnerable", "unknown", "not_evaluable", "skipped"]
    rules: Annotated[int, Field(ge=0)]
    evaluated_rules: Annotated[int, Field(ge=0)]
    vulnerable_rule_ids: list[int]
    reason: str


class CTILookupEvidence(Message):
    mapping: Literal["cve2owl-to-vulnerability-v1"] = "cve2owl-to-vulnerability-v1"
    contract: Literal["cve2owl-assessment-v1"] = "cve2owl-assessment-v1"
    backend_kind: Literal["real", "mock"]
    backend: Literal["cve2owl-symbolic-v1"]
    observed_software: SoftwareObservation
    # Nessun alias automatico: la query preserva il nome osservato. L'identità
    # restituita dal KG è documentata separatamente e può restare ambigua.
    identity_status: Literal["resolved", "ambiguous", "no_match"]
    identities: list[CTIIdentity]
    assessments: list[CTICVEAssessment]
    rule_coverage: Literal["complete", "partial", "none"]
    match_limit: int
    dataset_id: Text
    dataset_sha256: SHA256
    engine_sha256: dict[str, SHA256]
    request_sha256: SHA256
    response_sha256: SHA256
    response_file: Literal["cti_assessment.json"] = "cti_assessment.json"
    missing_metadata: list[Text]
    limitations: list[Text]
