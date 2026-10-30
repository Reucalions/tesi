"""Selezione dei backend prima dell'avvio degli agenti, mai decisa dall'LLM."""

import json
from contextlib import ExitStack, contextmanager
from pathlib import Path
from threading import Lock
from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from thesis_agents.mcp.settings import MCPSettings
from thesis_agents.telemetry.settings import StaticSource, TelemetryHTTPSettings
from thesis_agents.tools.sbom_http import NoSupplyChainSource, SupplyChainHTTPSettings


class LocalBackend(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    transport: Literal["local-mock"] = "local-mock"


Backend = Annotated[LocalBackend | MCPSettings, Field(discriminator="transport")]


class FabricProvenanceBinding(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    channel: str = Field(min_length=1)
    chaincode: str = Field(min_length=1)


class BackendSettings(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    version: Literal[1] = 1
    telemetry: Annotated[StaticSource | TelemetryHTTPSettings, Field(discriminator="transport")] = (
        Field(default_factory=StaticSource)
    )
    countermeasure_input: Annotated[
        NoSupplyChainSource | SupplyChainHTTPSettings, Field(discriminator="transport")
    ] = Field(default_factory=NoSupplyChainSource)
    vulnerability: Backend = Field(default_factory=LocalBackend)
    ranking: Backend = Field(default_factory=LocalBackend)
    semantic: Backend = Field(default_factory=LocalBackend)
    provenance: Backend = Field(default_factory=LocalBackend)
    vulnerability_adapter: Literal["lookup-v1", "cve2owl-v1", "ubuntu-package-v1"] = "lookup-v1"
    cti_dataset_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    ubuntu_sources_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    strategic_adapter: Literal["standard-v1", "empty-evidence-v1"] = "standard-v1"
    provenance_adapter: Literal["standard-v1", "fabric-native-v1"] = "standard-v1"
    fabric_provenance: FabricProvenanceBinding | None = None

    @model_validator(mode="after")
    def compatible_cti(self):
        if self.provenance_adapter == "fabric-native-v1":
            if (
                not isinstance(self.provenance, MCPSettings)
                or self.provenance.expected_kind != "real"
                or self.fabric_provenance is None
            ):
                raise ValueError(
                    "Fabric provenance requires a real MCP endpoint and ledger binding"
                )
        elif self.fabric_provenance is not None:
            raise ValueError("Fabric provenance binding requires the native adapter")
        if self.strategic_adapter == "empty-evidence-v1":
            if not all(
                isinstance(value, MCPSettings) and value.expected_kind == "real"
                for value in (self.ranking, self.provenance)
            ):
                raise ValueError(
                    "Evidence strategy gate requires real ranking and provenance MCP services"
                )
            if not isinstance(self.semantic, LocalBackend):
                raise ValueError("Evidence gate does not execute semantic validation")
        if isinstance(self.telemetry, TelemetryHTTPSettings) and isinstance(
            self.semantic, MCPSettings
        ):
            raise ValueError(
                "OpenTelemetry requires local semantic validation until a new MCP contract"
            )
        if self.vulnerability_adapter in ("cve2owl-v1", "ubuntu-package-v1"):
            if not isinstance(self.vulnerability, MCPSettings):
                raise ValueError(f"{self.vulnerability_adapter} richiede un endpoint MCP")
            if isinstance(self.semantic, MCPSettings):
                raise ValueError(
                    "Il contratto semantic-validation-v1 non rappresenta il nuovo report CTI; "
                    "usare semantic local-mock in questo incremento"
                )
        elif self.cti_dataset_sha256 is not None:
            raise ValueError("Il pin del dataset richiede l'adapter cve2owl-v1")
        if self.vulnerability_adapter == "ubuntu-package-v1":
            if not isinstance(self.telemetry, TelemetryHTTPSettings):
                raise ValueError(
                    "Ubuntu assessment requires HTTP telemetry with verified inventory"
                )
            if self.cti_dataset_sha256 is None or self.ubuntu_sources_sha256 is None:
                raise ValueError("Ubuntu assessment requires dataset and source manifest pins")
        elif self.ubuntu_sources_sha256 is not None:
            raise ValueError("Ubuntu source pin requires ubuntu-package-v1")
        return self

    @field_validator("vulnerability", "ranking", "semantic", "provenance", mode="before")
    @classmethod
    def legacy_local_profile(cls, value):
        # I profili del primo incremento usavano una stringa per i tre tool strategici.
        return {"transport": "local-mock"} if value == "local-mock" else value

    def remote_backends(self) -> dict[str, MCPSettings]:
        return {
            name: value
            for name in ("vulnerability", "ranking", "semantic", "provenance")
            if isinstance(value := getattr(self, name), MCPSettings)
        }

    @classmethod
    def load(cls, path: Path) -> "BackendSettings":
        return cls.model_validate_json(path.read_text())


class RunAudit:
    """Eventi del collegamento MCP; preparatori a PROV-O, non ricevute di ledger."""

    def __init__(self, path: Path, run_id: str):
        self.path = path
        self.run_id = run_id
        self._lock = Lock()
        path.touch(exist_ok=False)

    def __call__(self, event: dict):
        with self._lock, self.path.open("a", encoding="utf-8") as stream:
            stream.write(json.dumps({"run_id": self.run_id, **event}, ensure_ascii=False) + "\n")


@contextmanager
def connect_backends(session, settings: BackendSettings | None):
    """Configura la sessione prima di creare la Workforce e chiude MCP a fine run."""
    if settings is None:
        yield
        return
    # La modalità fixtures resta indipendente dalla rete, anche con un profilo esplicito.
    remote = settings.remote_backends()
    telemetry_http = isinstance(settings.telemetry, TelemetryHTTPSettings)
    supply_chain_http = isinstance(settings.countermeasure_input, SupplyChainHTTPSettings)
    from thesis_agents.schemas.telemetry_source import TelemetryInput

    if isinstance(session.case, TelemetryInput) != telemetry_http:
        raise ValueError(
            "TelemetryInput requires the HTTP telemetry profile, StaticTelemetry the static profile"
        )
    if session.mode == "fixtures" and (remote or telemetry_http or supply_chain_http):
        raise ValueError("La modalità fixtures richiede backend locali; usa mcp.probe o mode=camel")
    with (session.output_dir / "backends.json").open("x", encoding="utf-8") as stream:
        json.dump({"run_id": session.run_id, **settings.model_dump(mode="json")}, stream, indent=2)
        stream.write("\n")
    if telemetry_http:
        from thesis_agents.tools.telemetry_http import HTTPTelemetryTool

        session.telemetry_tool = HTTPTelemetryTool(
            settings.telemetry,
            RunAudit(session.output_dir / "telemetry_events.jsonl", session.run_id),
        )
    if supply_chain_http:
        from thesis_agents.tools.sbom_http import HTTPSupplyChainTool

        session.supply_chain_tool = HTTPSupplyChainTool(
            settings.countermeasure_input,
            RunAudit(session.output_dir / "supply_chain_events.jsonl", session.run_id),
        )
    if not remote:
        yield
        return

    # Import differiti: il percorso locale non carica lo stack HTTP MCP.
    from thesis_agents.mcp.client import MCPClient
    from thesis_agents.tools.cti_mcp import CTIVulnerabilityTool, cti_contracts
    from thesis_agents.tools.evidence_strategic_mcp import (
        EmptyEvidenceRankingTool,
        EvidenceProvenanceTool,
        evidence_provenance_contracts,
    )
    from thesis_agents.tools.fabric_provenance import (
        FabricProvenanceTool,
        fabric_provenance_contracts,
    )
    from thesis_agents.tools.strategic_mcp import (
        MCPProvenanceTool,
        MCPRankingTool,
        MCPSemanticTool,
        strategic_contracts,
    )
    from thesis_agents.tools.ubuntu_mcp import UbuntuVulnerabilityTool, ubuntu_contracts
    from thesis_agents.tools.vulnerability_mcp import MCPVulnerabilityTool, lookup_contracts

    audit = RunAudit(session.output_dir / "mcp_events.jsonl", session.run_id)
    with ExitStack() as stack:
        adapters = {}
        for name, config in remote.items():
            fabric_store = (
                name == "provenance" and settings.provenance_adapter == "fabric-native-v1"
            )
            evidence_store = (
                name == "provenance"
                and settings.strategic_adapter == "empty-evidence-v1"
                and not fabric_store
            )
            cti = name == "vulnerability" and settings.vulnerability_adapter == "cve2owl-v1"
            ubuntu = (
                name == "vulnerability" and settings.vulnerability_adapter == "ubuntu-package-v1"
            )
            contracts = (
                (ubuntu_contracts() if ubuntu else cti_contracts() if cti else lookup_contracts())
                if name == "vulnerability"
                else fabric_provenance_contracts()
                if fabric_store
                else evidence_provenance_contracts()
                if evidence_store
                else strategic_contracts(name)
            )
            client = stack.enter_context(
                MCPClient(
                    config,
                    contracts=contracts,
                    audit=lambda event, role=name: audit({**event, "backend_role": role}),
                )
            )
            if fabric_store:
                adapter = FabricProvenanceTool(
                    client,
                    session.output_dir,
                    channel=settings.fabric_provenance.channel,
                    chaincode=settings.fabric_provenance.chaincode,
                )
            elif name == "ranking" and settings.strategic_adapter == "empty-evidence-v1":
                adapter = EmptyEvidenceRankingTool(client)
            elif evidence_store:
                adapter = EvidenceProvenanceTool(client, session.output_dir)
            elif ubuntu:
                adapter = UbuntuVulnerabilityTool(
                    client,
                    session.output_dir,
                    dataset_sha256=settings.cti_dataset_sha256,
                    sources_sha256=settings.ubuntu_sources_sha256,
                )
            elif cti:
                adapter = CTIVulnerabilityTool(
                    client, session.output_dir, expected_dataset_sha256=settings.cti_dataset_sha256
                )
            elif name == "provenance":
                adapter = MCPProvenanceTool(client, session.output_dir / "provenance_receipt.json")
            else:
                adapter = {
                    "vulnerability": MCPVulnerabilityTool,
                    "ranking": MCPRankingTool,
                    "semantic": MCPSemanticTool,
                }[name](client)
            adapters[name] = adapter
        # Pubblica la configurazione solo dopo la discovery di tutti i servizi;
        # ExitStack chiude anche i precedenti se una connessione successiva fallisce.
        for name, adapter in adapters.items():
            setattr(session, f"{name}_tool", adapter)
        yield
