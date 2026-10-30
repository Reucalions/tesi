"""Servizio MCP: astensione su insieme vuoto e archivio PROV-O, senza BWAF/Fabric."""

import argparse
import json
from pathlib import Path
from threading import Lock

from mcp.server.fastmcp import FastMCP

from thesis_agents.mcp.client import digest
from thesis_agents.mcp.contracts import (
    PROVENANCE_CONTRACT,
    RANKING_CONTRACT,
    ProvenanceReceipt,
    ProvenanceRequest,
    ProvenanceResponse,
    RankingRequest,
    RankingResponse,
)
from thesis_agents.mcp.evidence_strategic_contracts import (
    ReadProvenanceRequest,
    ReadProvenanceResponse,
)
from thesis_agents.provenance import export_prov
from thesis_agents.schemas import ArgumentationGraph, ProvenanceRecord, RankingResult
from thesis_agents.schemas.base import Identifier

EMPTY_BACKEND = "empty-strategy-gate-v1"
STORE_BACKEND = "artifact-jsonld-store-v1"


def abstain_ranking(graph: ArgumentationGraph) -> RankingResult:
    if graph.arguments or graph.relations:
        raise ValueError(
            "Nonempty graphs require a validated BWAF mapping and service; no fallback"
        )
    return RankingResult(graph_id=graph.id, backend=EMPTY_BACKEND, ranking=[])


class ProvenanceStore:
    def __init__(self, root: Path):
        self.root = root
        root.mkdir(parents=True, exist_ok=True)
        self.lock = Lock()

    def read(self, run_id):
        request = ReadProvenanceRequest(run_id=run_id)
        directory = self.root / request.run_id
        record = ProvenanceRecord.model_validate_json((directory / "record.json").read_text())
        document = json.loads((directory / "provenance.jsonld").read_text())
        if record.run_id != run_id or document != export_prov(record):
            raise ValueError("Stored provenance differs from its deterministic export")
        return ReadProvenanceResponse(
            request_sha256=digest(request.model_dump(mode="json")),
            record=record,
            record_sha256=digest(record.model_dump(mode="json")),
            jsonld=document,
            jsonld_sha256=digest(document),
        )

    def store(self, record):
        ReadProvenanceRequest(run_id=record.run_id)
        document = export_prov(record)
        with self.lock:
            directory = self.root / record.run_id
            directory.mkdir(exist_ok=True)
            for name, data in (
                ("record.json", record.model_dump(mode="json")),
                ("provenance.jsonld", document),
            ):
                path = directory / name
                if path.exists():
                    if json.loads(path.read_text()) != data:
                        raise ValueError("Provenance storage is immutable for an existing run")
                else:
                    with path.open("x") as stream:
                        stream.write(json.dumps(data, indent=2) + "\n")
            persisted = self.read(record.run_id)
        return ProvenanceReceipt(
            run_id=record.run_id,
            stored=True,
            record_sha256=persisted.record_sha256,
            receipt_id=f"artifact:{record.run_id}:{persisted.record_sha256}",
            backend=STORE_BACKEND,
        )


def create_server(data_dir: Path, *, port=8007):
    server = FastMCP(
        "strategic-evidence-gateway",
        host="127.0.0.1",
        port=port,
        json_response=True,
        log_level="WARNING",
    )
    store = ProvenanceStore(data_dir)

    @server.tool()
    def rank_graph(graph: ArgumentationGraph) -> RankingResponse:
        """Return an empty ranking only; never simulate BWAF for a nonempty graph."""
        return RankingResponse(
            contract=RANKING_CONTRACT,
            backend_kind="real",
            backend=EMPTY_BACKEND,
            request_sha256=digest(RankingRequest(graph=graph).model_dump(mode="json")),
            result=abstain_ranking(graph),
        )

    @server.tool()
    def record_provenance(record: ProvenanceRecord) -> ProvenanceResponse:
        """Store JSON and PROV-O JSON-LD in files; no Fabric transaction."""
        return ProvenanceResponse(
            contract=PROVENANCE_CONTRACT,
            backend_kind="real",
            backend=STORE_BACKEND,
            request_sha256=digest(ProvenanceRequest(record=record).model_dump(mode="json")),
            result=store.store(record),
        )

    @server.tool()
    def read_provenance(run_id: Identifier) -> ReadProvenanceResponse:
        """Read back the stored record and PROV-O document for client verification."""
        return store.read(run_id)

    return server


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-dir", required=True, type=Path)
    parser.add_argument("--port", default=8007, type=int)
    args = parser.parse_args()
    create_server(args.data_dir, port=args.port).run(transport="streamable-http")


if __name__ == "__main__":
    main()
