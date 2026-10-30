"""Sintesi compatta per gli agenti; la risposta remota integrale rimane uno snapshot."""

from typing import Annotated, Literal

from pydantic import AwareDatetime, Field, StrictBool, model_validator

from .base import Message, Text
from .telemetry import SoftwareObservation

SHA256 = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
Count = Annotated[int, Field(ge=0, strict=True)]
CVE = Annotated[str, Field(pattern=r"^CVE-\d{4}-\d{4,}$")]
Verdict = Literal["fixed", "not_affected", "potentially_affected", "unknown"]
VERDICTS = ("fixed", "not_affected", "potentially_affected", "unknown")


class UbuntuPackageEvidence(Message):
    mapping: Literal["ubuntu-package-to-vulnerability-v1"] = "ubuntu-package-to-vulnerability-v1"
    contract: Literal["ubuntu-package-assessment-v1"] = "ubuntu-package-assessment-v1"
    backend_kind: Literal["real", "mock"]
    observed_software: SoftwareObservation
    identity_status: Literal[
        "resolved", "ambiguous", "no_match", "insufficient_evidence", "unreviewed"
    ]
    group_id: Literal["apache:http_server"] | None
    selected_identity_ids: list[Text]
    identity_candidate_counts: dict[Literal["equivalent", "excluded", "unresolved"], Count]
    search_scope: Literal["baseline-normalized-product-exact-and-token"] | None
    search_complete: StrictBool
    package_status: Literal["assessed", "not_assessed"]
    inventory_package: Literal["apache2"] = "apache2"
    inventory_version: Text
    distribution: Literal["Ubuntu"] = "Ubuntu"
    release: Literal["bionic"] = "bionic"
    inventory_collected_at: AwareDatetime
    facts_sha256: SHA256
    inventory_matches: StrictBool
    source_scope_matches: StrictBool
    scope: Literal["inventoried-package-retrospective-ubuntu-version-check"]
    runtime_applicability: Literal["not_assessed"] = "not_assessed"
    historical_runtime_state: Literal["not_established"] = "not_established"
    cve_ids_by_verdict: dict[Verdict, list[CVE]]
    counts: dict[Verdict, Count]
    dataset_sha256: SHA256
    identity_rule_sha256: SHA256
    source_manifest_sha256: SHA256
    request_sha256: SHA256
    response_sha256: SHA256
    response_file: Literal["ubuntu_package_assessment.json"] = "ubuntu_package_assessment.json"
    limitations: list[Text] = Field(min_length=1)

    @model_validator(mode="after")
    def coherent_summary(self):
        if set(self.identity_candidate_counts) != {"equivalent", "excluded", "unresolved"}:
            raise ValueError("All identity candidate dispositions must remain visible")
        resolved = self.identity_status == "resolved"
        if resolved != (self.group_id is not None) or resolved != bool(self.selected_identity_ids):
            raise ValueError("Only a resolved identity may retain a selected group")
        if resolved and (
            not self.search_complete
            or self.identity_candidate_counts["unresolved"]
            or self.identity_candidate_counts["equivalent"] != len(self.selected_identity_ids)
        ):
            raise ValueError("Identity selection requires complete reviewed search")
        if (self.package_status == "assessed") != (
            resolved and self.inventory_matches and self.source_scope_matches
        ):
            raise ValueError("Package status differs from identity and inventory binding")
        if set(self.cve_ids_by_verdict) != set(VERDICTS) or self.counts != {
            v: len(self.cve_ids_by_verdict[v]) for v in VERDICTS
        }:
            raise ValueError("Every package verdict must preserve its CVE IDs and count")
        ids = [cve for group in self.cve_ids_by_verdict.values() for cve in group]
        if len(ids) != len(set(ids)) or any(
            values != sorted(values) for values in self.cve_ids_by_verdict.values()
        ):
            raise ValueError("Package CVEs must be unique and sorted within each verdict")
        if self.package_status != "assessed" and ids:
            raise ValueError("Unsupported package assessment cannot classify CVEs")
        return self

    def lookup_status(self):
        # Identity and inventory knowledge do not attest the historical running process.
        return (
            self.identity_status
            if self.identity_status in ("ambiguous", "no_match")
            else "not_evaluable"
        )
