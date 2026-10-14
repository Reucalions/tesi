"""Prova di contratto MCP senza inferenza e senza simulare un'esecuzione degli agenti."""

import argparse
import json
import sys

from dotenv import load_dotenv

from thesis_agents.backends import BackendSettings
from thesis_agents.mcp.client import MCPClient
from thesis_agents.mcp.contracts import ProvenanceRequest, RankingRequest, SemanticRequest
from thesis_agents.mcp.cti_client import cti_contracts
from thesis_agents.mcp.settings import MCPSettings
from thesis_agents.schemas import SoftwareObservation
from thesis_agents.tools.cti_mcp import CTIVulnerabilityTool
from thesis_agents.tools.strategic_mcp import (
    MCPProvenanceTool,
    MCPRankingTool,
    MCPSemanticTool,
    strategic_contracts,
)
from thesis_agents.tools.vulnerability_mcp import MCPVulnerabilityTool, lookup_contracts


def main(argv=None) -> int:
    from pathlib import Path

    parser = argparse.ArgumentParser(description="Verifica configurazione e tool MCP senza LLM")
    parser.add_argument("--backends", type=Path, required=True)
    parser.add_argument(
        "--check-config", action="store_true", help="Solo handshake/discovery, nessuna tools/call"
    )
    parser.add_argument(
        "--service",
        choices=("vulnerability", "ranking", "semantic", "provenance"),
        default="vulnerability",
    )
    parser.add_argument("--request", type=Path, help="JSON del contratto di richiesta strategico")
    parser.add_argument("--receipt", type=Path, help="File nuovo per la ricevuta di provenienza")
    parser.add_argument("--package", default="log4j-core")
    parser.add_argument("--version", default="2.14.1")
    parser.add_argument("--evidence-id", default="E1")
    parser.add_argument("--output-dir", type=Path, help="Nuova directory per lo snapshot cve2owl")
    args = parser.parse_args(argv)
    try:
        load_dotenv(Path.cwd() / ".env", override=False)
        profile = BackendSettings.load(args.backends)
        lookup_schema = (
            cti_contracts if profile.vulnerability_adapter == "cve2owl-v1" else lookup_contracts
        )
        if args.check_config:
            events, checked = [], []
            for name, settings in profile.remote_backends().items():
                contracts = (
                    lookup_schema() if name == "vulnerability" else strategic_contracts(name)
                )
                with MCPClient(
                    settings,
                    contracts=contracts,
                    audit=lambda event, role=name: events.append({**event, "backend_role": role}),
                ) as client:
                    checked.append(
                        {"service": name, "tools": list(contracts), "server": client.server_info}
                    )
            print(json.dumps({"checked": checked, "mcp_events": events}, indent=2))
            return 0
        settings = getattr(profile, args.service)
        if not isinstance(settings, MCPSettings):
            raise ValueError(f"Il probe richiede un backend {args.service} MCP")
        request = None
        if args.service != "vulnerability":
            if not args.request:
                raise ValueError("I tool strategici richiedono --request con il relativo JSON")
            schema = {
                "ranking": RankingRequest,
                "semantic": SemanticRequest,
                "provenance": ProvenanceRequest,
            }[args.service]
            request = schema.model_validate_json(args.request.read_text(encoding="utf-8"))
        if args.service == "provenance" and not args.receipt:
            raise ValueError("La registrazione richiede --receipt per salvare la ricevuta")
        events = []
        contracts = (
            lookup_schema()
            if args.service == "vulnerability"
            else strategic_contracts(args.service)
        )
        with MCPClient(settings, contracts=contracts, audit=events.append) as client:
            if args.service == "vulnerability":
                if profile.vulnerability_adapter == "cve2owl-v1":
                    if args.output_dir is None:
                        raise ValueError("Il probe cve2owl richiede --output-dir per lo snapshot")
                    args.output_dir.mkdir(parents=True, exist_ok=False)
                    adapter = CTIVulnerabilityTool(
                        client, args.output_dir, expected_dataset_sha256=profile.cti_dataset_sha256
                    )
                else:
                    adapter = MCPVulnerabilityTool(client)
                result = adapter.lookup_vulnerabilities(
                    SoftwareObservation(
                        package=args.package, version=args.version, evidence_id=args.evidence_id
                    )
                ).model_dump(mode="json")
            elif args.service == "ranking":
                result = MCPRankingTool(client).rank_graph(request.graph).model_dump(mode="json")
            elif args.service == "semantic":
                result = (
                    MCPSemanticTool(client)
                    .validate_countermeasure(request.strategy, request.context)
                    .model_dump(mode="json")
                )
            else:
                result = MCPProvenanceTool(client, args.receipt).record_provenance(request.record)
        print(json.dumps({"result": result, "mcp_events": events}, indent=2))
        return 0
    except (ValueError, OSError, RuntimeError) as exc:
        print(f"Errore MCP: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
