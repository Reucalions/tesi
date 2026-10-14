"""Contratto dell'ingresso SBOM/OSV; non modifica i finding autorevoli del KG.

Il primo adapter supporta componenti Maven in CycloneDX JSON 1.5/1.6.
I modelli OSV validano i campi utilizzati e conservano il resto nello snapshot;
non sono una reimplementazione completa degli standard CycloneDX e OSV.
"""

from typing import Annotated, Literal

from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from thesis_agents.mcp.client import digest

from .base import Identifier, Message, Text, require_unique
from .telemetry import SoftwareObservation
from .telemetry_source import SHA256

OSV_URL = "https://api.osv.dev/v1/query"
MavenPart = Annotated[str, Field(pattern=r"^[A-Za-z0-9_.-]+$")]


class SupplyChainQuery(Message):
    service_name: Identifier
    software: SoftwareObservation


class AssetBinding(Message):
    service_name: Identifier
    runtime_package: Text
    component_ref: Text


class MavenComponent(Message):
    bom_ref: Text
    group: MavenPart
    name: MavenPart
    version: Annotated[str, Field(pattern=r"^[A-Za-z0-9_.+-]+$")]
    purl: Text

    @model_validator(mode="after")
    def consistent_purl(self):
        base = f"pkg:maven/{self.group}/{self.name}@{self.version}"
        # Il plugin CycloneDX Maven identifica il normale artefatto con type=jar.
        # Altri tipi/classifier non vengono eliminati implicitamente dalla query OSV.
        if self.purl not in (base, base + "?type=jar"):
            raise ValueError(
                "Expected a Maven purl matching group/name/version, with optional type=jar only"
            )
        return self

    def osv_query(self):
        return {
            "package": {"ecosystem": "Maven", "name": f"{self.group}:{self.name}"},
            "version": self.version,
        }


def select_component(document: dict, binding: AssetBinding, query: SupplyChainQuery):
    """Associazione esplicita asset -> bom-ref; nessun alias deciso dal modello."""
    if document.get("bomFormat") != "CycloneDX" or document.get("specVersion") not in (
        "1.5",
        "1.6",
    ):
        raise ValueError("Expected CycloneDX JSON 1.5/1.6")
    if (binding.service_name, binding.runtime_package) != (
        query.service_name,
        query.software.package,
    ):
        raise ValueError("SBOM binding does not match runtime asset/package")
    components = document.get("components")
    if not isinstance(components, list) or not 1 <= len(components) <= 500:
        raise ValueError("Expected 1..500 top-level SBOM components")
    # Il sottoinsieme accettato è esplicito: non si ignorano componenti annidati.
    if any(not isinstance(c, dict) or c.get("components") for c in components):
        raise ValueError("Nested or malformed SBOM components are not supported")
    refs = [c.get("bom-ref") for c in components]
    if any(not isinstance(ref, str) or not ref for ref in refs):
        raise ValueError("Every component requires a bom-ref")
    require_unique(refs, "SBOM component references")
    matches = [c for c in components if c["bom-ref"] == binding.component_ref]
    if len(matches) != 1:
        raise ValueError("Configured SBOM component not found")
    c = matches[0]
    component = MavenComponent.model_validate(
        {
            "bom_ref": c["bom-ref"],
            "group": c.get("group"),
            "name": c.get("name"),
            "version": c.get("version"),
            "purl": c.get("purl"),
        }
    )
    if component.version != query.software.version:
        raise ValueError("SBOM version differs from runtime evidence")
    return component


class OSVObject(BaseModel):
    model_config = ConfigDict(extra="allow")


class OSVEvent(Message):
    introduced: Text | None = None
    fixed: Text | None = None
    last_affected: Text | None = None
    limit: Text | None = None

    @model_validator(mode="after")
    def one_boundary(self):
        if (
            sum(
                v is not None for v in (self.introduced, self.fixed, self.last_affected, self.limit)
            )
            != 1
        ):
            raise ValueError("OSV event must have exactly one boundary")
        return self


class OSVRange(OSVObject):
    type: Literal["SEMVER", "ECOSYSTEM", "GIT"]
    repo: Text | None = None
    events: list[OSVEvent] = Field(min_length=1, max_length=200)


class OSVPackage(OSVObject):
    ecosystem: Text
    name: Text


class OSVAffected(OSVObject):
    package: OSVPackage
    ranges: list[OSVRange] = Field(default_factory=list, max_length=100)
    versions: list[Text] = Field(default_factory=list)


class OSVRecord(OSVObject):
    id: Text
    modified: AwareDatetime
    withdrawn: AwareDatetime | None = None
    aliases: list[Text] = Field(default_factory=list)
    affected: list[OSVAffected] = Field(default_factory=list)


class OSVResponse(Message):
    vulns: list[OSVRecord] = Field(default_factory=list, max_length=200)
    next_page_token: Text | None = None


class OSVExchange(Message):
    request: dict
    response: dict


class SupplyChainSnapshot(Message):
    contract: Literal["sbom-osv-v1"] = "sbom-osv-v1"
    backend: Literal["sbom-osv-http-v1"] = "sbom-osv-http-v1"
    source_id: Identifier
    sbom_kind: Literal["demo", "provided"]
    osv_kind: Literal["live", "mock"]
    osv_url: Text
    acquired_at: AwareDatetime
    query: SupplyChainQuery
    request_sha256: SHA256
    binding: AssetBinding
    source_sha256: SHA256
    document_sha256: SHA256
    document: dict
    pages: list[OSVExchange] = Field(min_length=1, max_length=10)

    @model_validator(mode="after")
    def coherent_assessment(self):
        component = select_component(self.document, self.binding, self.query)
        if self.request_sha256 != digest(
            self.query.model_dump(mode="json")
        ) or self.document_sha256 != digest(self.document):
            raise ValueError("SBOM snapshot digest mismatch")
        if self.osv_kind == "live" and self.osv_url != OSV_URL:
            raise ValueError("Live OSV requires the official query endpoint")
        expected = component.osv_query()
        seen_tokens, ids = set(), []
        for index, page in enumerate(self.pages):
            if page.request != expected:
                raise ValueError("OSV query or pagination does not match selected component")
            response = OSVResponse.model_validate(page.response)
            ids.extend(v.id for v in response.vulns)
            token = response.next_page_token
            if token:
                if token in seen_tokens or index == len(self.pages) - 1:
                    raise ValueError("Incomplete or repeated OSV pagination")
                seen_tokens.add(token)
                expected = component.osv_query() | {"page_token": token}
            elif index != len(self.pages) - 1:
                raise ValueError("Unexpected page after complete OSV response")
        require_unique(ids, "OSV advisory IDs")
        if len(ids) > 200:
            raise ValueError("Too many OSV advisories for this prototype")
        return self


class AdvisoryContext(Message):
    id: Text
    matched_cves: list[Text]
    # Solo i range del pacchetto esatto; non sono una versione di upgrade scelta.
    ranges: list[OSVRange]


class CountermeasureContext(Message):
    source_id: Identifier
    sbom_kind: Literal["demo", "provided"]
    osv_kind: Literal["live", "mock"]
    snapshot_file: Literal["supply_chain_snapshot.json"] = "supply_chain_snapshot.json"
    snapshot_sha256: SHA256
    component: MavenComponent
    runtime_evidence_id: Identifier
    report_sha256: SHA256
    advisories: list[AdvisoryContext]
    other_osv_ids: list[Text]
    withdrawn_ids: list[Text]
    uncorrelated_ids: list[Text]
    report_cves_without_osv_match: list[Text]
    limitations: list[Text]


def countermeasure_context(snapshot: SupplyChainSnapshot, report) -> CountermeasureContext:
    """Proiezione ripetibile: alias espliciti, senza ricalcolare range o CVSS."""
    component = select_component(snapshot.document, snapshot.binding, snapshot.query)
    known = {v.cve_id for v in report.vulnerabilities}
    advisories, other, withdrawn, uncorrelated, covered = [], [], [], [], set()
    for page in snapshot.pages:
        for v in OSVResponse.model_validate(page.response).vulns:
            if v.withdrawn is not None:
                withdrawn.append(v.id)
                continue
            affected = [
                a
                for a in v.affected
                if a.package.ecosystem == "Maven"
                and a.package.name == f"{component.group}:{component.name}"
            ]
            if not affected:
                uncorrelated.append(v.id)
                continue
            matched = sorted(known & {v.id, *v.aliases})
            if not matched:
                other.append(v.id)
                continue
            covered.update(matched)
            advisories.append(
                AdvisoryContext(
                    id=v.id, matched_cves=matched, ranges=[r for a in affected for r in a.ranges]
                )
            )
    context = CountermeasureContext(
        source_id=snapshot.source_id,
        sbom_kind=snapshot.sbom_kind,
        osv_kind=snapshot.osv_kind,
        snapshot_sha256=digest(snapshot.model_dump(mode="json")),
        component=component,
        runtime_evidence_id=snapshot.query.software.evidence_id,
        report_sha256=digest(report.model_dump(mode="json")),
        advisories=advisories,
        other_osv_ids=other,
        withdrawn_ids=withdrawn,
        uncorrelated_ids=uncorrelated,
        report_cves_without_osv_match=sorted(known - covered),
        limitations=[
            "SBOM is a declared inventory; its binding is configured, not runtime attestation.",
            "Only one bound Maven component is queried, not the entire dependency graph.",
            "OSV results enrich the CTI report without replacing it or adding confirmed CVEs.",
            "No OSV match does not prove safety. Withdrawn or uncorrelated records are excluded.",
            "Range events retain their meaning and branches; fixed is not a globally safe target.",
            "Upgrade targets still require vendor, compatibility and all-advisory checks.",
        ],
    )
    if len(context.model_dump_json().encode("utf-8")) > 32 * 1024:
        raise ValueError("Supply chain context exceeds 32 KiB; no silent truncation")
    return context
