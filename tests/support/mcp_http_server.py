"""Processo server per test HTTP reali; i guasti non entrano nel codice applicativo."""

import argparse
import asyncio
import os
import socket
from pathlib import Path

import uvicorn
from cti_http_server import create_server as create_cti_server

from thesis_agents.mcp.client import digest
from thesis_agents.mcp.contracts import (
    LOOKUP_CONTRACT,
    LOOKUP_TOOL,
    PROVENANCE_CONTRACT,
    PROVENANCE_TOOL,
    RANKING_CONTRACT,
    RANKING_TOOL,
    SEMANTIC_CONTRACT,
    SEMANTIC_TOOL,
    LookupResponse,
    ProvenanceRequest,
    ProvenanceResponse,
    RankingRequest,
    RankingResponse,
    SemanticRequest,
    SemanticResponse,
)
from thesis_agents.mcp.mock_server import create_server
from thesis_agents.mcp.strategic_mock_server import MockProvenanceStore
from thesis_agents.mcp.strategic_mock_server import create_server as create_strategic_server
from thesis_agents.mcp.v1_domain import DecisionContext
from thesis_agents.schemas import (
    ArgumentationGraph,
    CountermeasureCandidate,
    ProvenanceRecord,
    SoftwareObservation,
)
from thesis_agents.tools.ranking_mock import MockRankingTool
from thesis_agents.tools.semantic_mock import MockSemanticTool
from thesis_agents.tools.vulnerability_mock import MockVulnerabilityTool


def strategic_fault(server, fault, data_dir):
    # I guasti mantengono schemi corretti per esercitare i controlli sui riferimenti.
    service, _, error = fault.partition(":")

    def metadata(request, backend):
        return {
            "backend_kind": "real" if error == "wrong-kind" else "mock",
            "backend": "unrelated-backend" if error == "wrong-backend" else backend,
            "request_sha256": "0" * 64 if error == "wrong-request" else digest(request),
        }

    if service == "ranking":
        server.remove_tool(RANKING_TOOL)
        if error == "missing":
            return

        @server.tool(name=RANKING_TOOL)
        def faulty_rank(graph: ArgumentationGraph) -> RankingResponse:
            result = MockRankingTool().rank_graph(graph)
            if error == "wrong-id":
                result.graph_id = "unrelated"
            if error == "missing-strategy":
                result.ranking = result.ranking[1:]
            return RankingResponse(
                contract=RANKING_CONTRACT,
                result=result,
                **metadata(RankingRequest(graph=graph).model_dump(mode="json"), result.backend),
            )
    elif service == "semantic":
        server.remove_tool(SEMANTIC_TOOL)

        @server.tool(name=SEMANTIC_TOOL)
        def faulty_semantic(
            strategy: CountermeasureCandidate, context: DecisionContext
        ) -> SemanticResponse:
            result = MockSemanticTool().validate_countermeasure(strategy, context)
            if error == "wrong-id":
                result.strategy_id = "unrelated"
            return SemanticResponse(
                contract=SEMANTIC_CONTRACT,
                result=result,
                **metadata(
                    SemanticRequest(strategy=strategy, context=context).model_dump(mode="json"),
                    result.backend,
                ),
            )
    elif service == "provenance":
        server.remove_tool(PROVENANCE_TOOL)
        store = MockProvenanceStore(data_dir)

        @server.tool(name=PROVENANCE_TOOL)
        def faulty_provenance(record: ProvenanceRecord) -> ProvenanceResponse:
            result = store.record_provenance(record)
            if error == "wrong-id":
                result.run_id = "unrelated"
            if error == "wrong-record":
                result.record_sha256 = "0" * 64
            if error == "not-stored":
                result.stored = False
            return ProvenanceResponse(
                contract=PROVENANCE_CONTRACT,
                result=result,
                **metadata(
                    ProvenanceRequest(record=record).model_dump(mode="json"), result.backend
                ),
            )


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fd", type=int, required=True)
    parser.add_argument("--fault", default="none")
    parser.add_argument("--kind", choices=("lookup", "strategic", "cti"), default="lookup")
    parser.add_argument("--data-dir", type=Path, required=True)
    args = parser.parse_args()
    server = (
        create_strategic_server(data_dir=args.data_dir)
        if args.kind == "strategic"
        else create_server()
    )
    if args.kind == "cti":
        server = create_cti_server(args.fault)
    if args.kind == "strategic" and args.fault != "none":
        strategic_fault(server, args.fault, args.data_dir)
    elif args.kind == "lookup" and args.fault != "none":
        server.remove_tool(LOOKUP_TOOL)
        if args.fault == "bad-schema":

            @server.tool(name=LOOKUP_TOOL)
            def incompatible(software: str) -> LookupResponse:
                raise AssertionError("Discovery should reject this tool")
        elif args.fault != "missing":

            @server.tool(name=LOOKUP_TOOL)
            async def faulty(software: SoftwareObservation) -> LookupResponse:
                if args.fault == "disconnect":
                    os._exit(2)  # Solo il processo server di prova viene terminato.
                if args.fault == "timeout":
                    await asyncio.sleep(10)
                if args.fault == "tool-error":
                    raise RuntimeError("Simulated remote error")
                result = MockVulnerabilityTool().lookup_vulnerabilities(software)
                if args.fault == "wrong-evidence":
                    result.vulnerabilities[0].evidence_ids = ["UNRELATED"]
                if args.fault == "wrong-version":
                    result.vulnerabilities[0].observed_version = "0.0.0"
                return LookupResponse(
                    contract=LOOKUP_CONTRACT,
                    backend_kind="real" if args.fault == "wrong-kind" else "mock",
                    backend="test-server",
                    result=result,
                )

    # Il socket è riservato dal processo padre: nessuna gara per una porta libera.
    with socket.socket(fileno=args.fd) as listener:
        uvicorn.Server(uvicorn.Config(server.streamable_http_app(), log_level="error")).run(
            sockets=[listener]
        )


if __name__ == "__main__":
    main()
