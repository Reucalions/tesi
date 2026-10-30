"""Applicabilità al pacchetto inventariato, distinta da identità e stato runtime."""

from typing import Annotated, Literal

from pydantic import AwareDatetime, Field, StrictBool, model_validator

from .cti_contracts import SHA256, Count, Message, Text
from .identity_contracts import IdentityRequest
from .identity_v2_contracts import IdentityResolution

TOOL = "assess_ubuntu_package"
CONTRACT = "ubuntu-package-assessment-v1"
Verdict = Literal["fixed", "not_affected", "potentially_affected", "unknown"]
VERDICTS = ("fixed", "not_affected", "potentially_affected", "unknown")
CVE = Annotated[str, Field(pattern=r"^CVE-\d{4}-\d{4,}$")]


class PackageRequest(Message):
    identity: IdentityRequest
    distribution: Literal["Ubuntu"]
    release: Literal["bionic"]
    release_version: Literal["18.04"]


class SourceReference(Message):
    url: Text
    sha256: SHA256


class SourceFile(SourceReference):
    file: Annotated[str, Field(pattern=r"^[A-Za-z0-9_.-]+$")]


class CVESourceFile(Message):
    cve_id: CVE
    url: Text
    file: Annotated[str, Field(pattern=r"^CVE-\d{4}-\d{4,}\.json$")]
    sha256: SHA256 | None
    error: str | None

    @model_validator(mode="after")
    def valid_source(self):
        if self.file != self.cve_id + ".json" or (self.sha256 is None) == (self.error is None):
            raise ValueError("A source must be either downloaded or explicitly unavailable")
        return self


class SourcesManifest(Message):
    contract: Literal["ubuntu-cve-snapshot-v1"] = "ubuntu-cve-snapshot-v1"
    kind: Literal["real", "fixture"]
    prepared_at: AwareDatetime
    identity_dataset_sha256: SHA256
    identity_rule_sha256: SHA256
    facts: SourceFile
    packaging_notice: SourceFile
    records: list[CVESourceFile]

    @model_validator(mode="after")
    def unique_records(self):
        ids = [r.cve_id for r in self.records]
        if ids != sorted(set(ids)):
            raise ValueError("Snapshot CVE records must be sorted and unique")
        return self


class InventoryPackage(Message):
    name: Literal["apache2", "apache2-bin"]
    version: Text
    arch: Text
    origin: Literal["Ubuntu"]
    manager: Literal["apt"]


class InventoryBinding(Message):
    host: Text
    distribution: Text
    release: Text
    release_version: Text
    collected_at: AwareDatetime
    facts_sha256: SHA256
    source_package: Literal["apache2"] = "apache2"
    packages: list[InventoryPackage]
    packaging_notice: SourceReference


class UbuntuStatus(Message):
    pointer: Annotated[str, Field(pattern=r"^/packages/\d+/statuses/\d+$")]
    status: Text
    description: str | None
    pocket: str | None


class CVEAssessment(Message):
    cve_id: CVE
    identity_ids: list[Text] = Field(min_length=1)
    verdict: Verdict
    reason: Text
    source: SourceReference | None
    ubuntu_statuses: list[UbuntuStatus]
    ubuntu_published: str | None
    ubuntu_updated_at: str | None
    version_boundary: Annotated[str, Field(pattern=r"^(?:[0-9]+:)?[0-9][A-Za-z0-9.+:~\-]*$")] | None
    comparison: Literal["lt", "eq", "gt"] | None

    @model_validator(mode="after")
    def justified_verdict(self):
        if (self.version_boundary is None) != (self.comparison is None):
            raise ValueError("Version boundary and Debian comparison must remain together")
        if self.verdict != "unknown" and (self.source is None or len(self.ubuntu_statuses) != 1):
            raise ValueError("A conclusive package verdict requires one Ubuntu release status")
        if self.verdict != "unknown":
            status = self.ubuntu_statuses[0]
            if self.verdict == "fixed" and (
                status.status != "released" or self.comparison not in ("eq", "gt")
            ):
                raise ValueError("A fixed verdict requires a reached Ubuntu fix version")
            if self.verdict == "not_affected" and status.status != "not-affected":
                raise ValueError("Not affected requires an explicit Ubuntu status")
            if self.verdict == "not_affected" and self.comparison == "lt":
                raise ValueError("An older package cannot inherit a later not-affected boundary")
            if self.verdict == "potentially_affected" and not (
                (status.status == "released" and self.comparison == "lt")
                or status.status in ("needed", "pending", "deferred")
            ):
                raise ValueError("Potential applicability requires Ubuntu evidence")
        return self


class PackageAssessment(Message):
    contract: Literal["ubuntu-package-assessment-v1"] = CONTRACT
    backend_kind: Literal["real", "mock"]
    request_sha256: SHA256
    request: PackageRequest
    identity_resolution: IdentityResolution
    source_manifest_sha256: SHA256
    source_identity_dataset_sha256: SHA256
    source_identity_rule_sha256: SHA256
    sources_prepared_at: AwareDatetime
    engine_sha256: dict[str, SHA256] = Field(min_length=1)
    comparator: Text
    inventory: InventoryBinding
    inventory_matches: StrictBool
    source_scope_matches: StrictBool
    status: Literal["assessed", "not_assessed"]
    reason: Text
    scope: Literal["inventoried-package-retrospective-ubuntu-version-check"]
    runtime_applicability: Literal["not_assessed"] = "not_assessed"
    historical_runtime_state: Literal["not_established"] = "not_established"
    results: list[CVEAssessment]
    counts: dict[Verdict, Count]
    limitations: list[Text] = Field(min_length=1)

    @model_validator(mode="after")
    def complete_results(self):
        identity = self.identity_resolution
        if (
            identity.evidence != self.request.identity.evidence
            or identity.backend_kind != self.backend_kind
        ):
            raise ValueError("Package and identity assessments must preserve the same evidence")
        evidence = self.request.identity.evidence
        inventory = self.inventory
        packages = inventory.packages
        matches = (
            inventory.host == evidence.host
            and inventory.distribution == self.request.distribution
            and inventory.release == self.request.release
            and inventory.release_version == self.request.release_version
            and inventory.facts_sha256 == evidence.facts_sha256
            and inventory.collected_at == evidence.facts_collected_at
            and evidence.inventory_package == "apache2"
            and evidence.inventory_origin == "Ubuntu"
            and len(packages) == 2
            and {p.name for p in packages} == {"apache2", "apache2-bin"}
            and all(p.version == evidence.inventory_version for p in packages)
        )
        if self.inventory_matches != matches:
            raise ValueError("Inventory match differs from the pinned facts")
        scope_matches = (
            identity.search is not None
            and identity.search.dataset.sha256 == self.source_identity_dataset_sha256
            and identity.rule_sha256 == self.source_identity_rule_sha256
        )
        if self.source_scope_matches != scope_matches:
            raise ValueError("Source scope differs from the pinned identity revision")
        eligible = (
            identity.status == "resolved" and self.inventory_matches and self.source_scope_matches
        )
        if (self.status == "assessed") != eligible:
            raise ValueError("Only matching inventory and resolved identity may be assessed")
        expected = {}
        if eligible:
            for candidate in identity.candidates:
                if candidate.canonical_id in identity.selected_identity_ids:
                    for cve in candidate.cve_ids:
                        expected.setdefault(cve, set()).add(candidate.canonical_id)
        if [r.cve_id for r in self.results] != sorted(expected):
            raise ValueError("Every unique selected CVE must have exactly one result")
        for result in self.results:
            if result.identity_ids != sorted(expected[result.cve_id]):
                raise ValueError("CVE origins must preserve all selected identity aliases")
        if self.counts != {v: sum(r.verdict == v for r in self.results) for v in VERDICTS}:
            raise ValueError("Package counts differ from the individual verdicts")
        return self


__all__ = [
    "CONTRACT",
    "TOOL",
    "CVEAssessment",
    "CVESourceFile",
    "InventoryBinding",
    "InventoryPackage",
    "PackageAssessment",
    "PackageRequest",
    "SourceFile",
    "SourceReference",
    "SourcesManifest",
    "UbuntuStatus",
    "VERDICTS",
]
