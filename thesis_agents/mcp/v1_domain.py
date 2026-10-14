"""Contratti wire v1 congelati prima dell'adapter cve2owl: non estenderli implicitamente."""

# Contratti del lookup e del report pubblicato da VulnerabilityAgent.
# Le CVE sono correlate all'evidenza originale tramite ID; il report non ingloba
# RuntimeEvidence e non ne diventa il sostituto per gli agenti successivi.
from typing import Annotated, Literal

from pydantic import Field, StrictBool, model_validator

from thesis_agents.schemas.base import Identifier, Message, Text, UnitScore, require_unique
from thesis_agents.schemas.telemetry import SoftwareObservation


class RuntimeEvidence(Message):
    """Schema wire storico: i nuovi metadati OTEL richiedono un altro contratto."""

    service_name: Identifier
    software: list[SoftwareObservation] = Field(min_length=1)
    endpoint_exposed: StrictBool
    deserialization_observed: StrictBool
    observations: list[Text]

    @model_validator(mode="after")
    def unique_evidence(self):
        require_unique([s.evidence_id for s in self.software], "evidence IDs")
        return self


class VulnerabilityFinding(Message):
    # La regex controlla la forma dell'identificatore CVE, non la sua esistenza.
    cve_id: Annotated[str, Field(pattern=r"^CVE-\d{4}-\d{4,}$")]
    package: Text
    observed_version: Text
    cvss: Annotated[float, Field(ge=0, le=10, allow_inf_nan=False)]
    # CVSS usa la scala 0..10; confidence invece la scala 0..1. CWE identifica
    # categorie di debolezza. I valori del mock sono fixture, non una misura live.
    cwe: list[Text]
    confidence: UnitScore
    evidence_ids: list[Identifier] = Field(min_length=1)
    # Il collegamento alle osservazioni e la fonte spiegano da dove arriva il finding.
    source: Text


class LookupResult(Message):
    # Risposta del backend prima della pubblicazione del report. «unsupported»
    # significa che il mock non copre il caso, non che il software è privo di CVE.
    status: Literal["matched", "unsupported"]
    vulnerabilities: list[VulnerabilityFinding]


class VulnerabilityReport(Message):
    # Output pubblico dell'agente: aggiunge l'identità del servizio alla risposta
    # del lookup. I finding restano quelli del tool, verificati da ArtifactSession.
    asset_id: Identifier
    lookup_status: Literal["matched", "unsupported"]
    vulnerabilities: list[VulnerabilityFinding]

    @model_validator(mode="after")
    def check_findings(self):
        # Evita CVE duplicate e stati contraddittori: matched richiede almeno un
        # finding, mentre unsupported deve avere una lista vuota.
        require_unique([v.cve_id for v in self.vulnerabilities], "CVE IDs")
        if (self.lookup_status == "matched") != bool(self.vulnerabilities):
            raise ValueError("Matched reports require findings; unsupported reports must be empty")
        return self


class DecisionContext(Message):
    evidence: RuntimeEvidence
    vulnerabilities: VulnerabilityReport
    available_capabilities: list[Text]
    prohibited_actions: list[Text]


def legacy_payload(value):
    """Rimuove solo il campo nuovo assente; rifiuta dati CTI reali nel wire v1."""
    data = value.model_dump(mode="json") if hasattr(value, "model_dump") else dict(value)
    if "evidence" in data:
        evidence = dict(data["evidence"])
        if evidence.get("telemetry") is not None:
            raise ValueError("Il contratto MCP v1 non rappresenta il contesto OpenTelemetry")
        evidence.pop("telemetry", None)
        data["evidence"] = evidence
    report = data.get("vulnerabilities") if "evidence" in data else data
    if isinstance(report, dict) and "cti" in report:
        if report["cti"] is not None:
            raise ValueError("Il contratto MCP v1 non rappresenta il contesto cve2owl")
        del report["cti"]
    return data
