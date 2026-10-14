"""Server MCP separato per ranking, validazione e audit dimostrativi.

Gli algoritmi restano i mock esistenti. Solo questo processo accede ai backend;
la persistenza SQLite delle ricevute non è un ledger Fabric né PROV-O.
"""

import argparse
import json
import sqlite3
from contextlib import closing
from pathlib import Path

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from thesis_agents.mcp.client import digest
from thesis_agents.mcp.contracts import (
    PROVENANCE_CONTRACT,
    RANKING_CONTRACT,
    SEMANTIC_CONTRACT,
    ProvenanceReceipt,
    ProvenanceRequest,
    ProvenanceResponse,
    RankingRequest,
    RankingResponse,
    SemanticRequest,
    SemanticResponse,
)
from thesis_agents.mcp.v1_domain import DecisionContext
from thesis_agents.schemas import (
    ArgumentationGraph,
    CountermeasureCandidate,
    ProvenanceRecord,
)
from thesis_agents.tools.ranking_mock import MockRankingTool
from thesis_agents.tools.semantic_mock import MockSemanticTool


class MockProvenanceStore:
    """Scrittura idempotente per run: stesso record ammesso, contenuto diverso rifiutato."""

    backend = "sqlite-provenance-mock-v1"

    def __init__(self, data_dir: Path):
        data_dir.mkdir(parents=True, exist_ok=True)
        self.database = data_dir / "provenance.sqlite3"
        with closing(sqlite3.connect(self.database)) as connection, connection:
            connection.execute(
                "CREATE TABLE IF NOT EXISTS records "
                "(run_id TEXT PRIMARY KEY, payload TEXT NOT NULL)"
            )

    def record_provenance(self, record: ProvenanceRecord) -> ProvenanceReceipt:
        data = record.model_dump(mode="json")
        payload = json.dumps(data, sort_keys=True, ensure_ascii=False, allow_nan=False)
        with closing(sqlite3.connect(self.database)) as connection, connection:
            connection.execute(
                "INSERT OR IGNORE INTO records(run_id, payload) VALUES (?, ?)",
                (record.run_id, payload),
            )
            stored = connection.execute(
                "SELECT payload FROM records WHERE run_id = ?", (record.run_id,)
            ).fetchone()[0]
            if stored != payload:
                raise ValueError("A different provenance record already exists for this run")
        record_hash = digest(data)
        return ProvenanceReceipt(
            run_id=record.run_id,
            stored=True,
            record_sha256=record_hash,
            receipt_id=f"mock:{record_hash}",
            backend=self.backend,
        )


def create_server(*, data_dir: Path, host: str = "127.0.0.1", port: int = 8002) -> FastMCP:
    server = FastMCP(
        "thesis-strategic-mock", host=host, port=port, json_response=True, log_level="WARNING"
    )
    ranking = MockRankingTool()
    semantic = MockSemanticTool()
    provenance = MockProvenanceStore(data_dir)

    @server.tool(annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True))
    def rank_graph(graph: ArgumentationGraph) -> RankingResponse:
        """Rank the graph with the illustrative one-hop mock, not the BWAF contract."""
        result = ranking.rank_graph(graph)
        return RankingResponse(
            contract=RANKING_CONTRACT,
            backend_kind="mock",
            backend=result.backend,
            request_sha256=digest(RankingRequest(graph=graph).model_dump(mode="json")),
            result=result,
        )

    @server.tool(annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True))
    def validate_countermeasure(
        strategy: CountermeasureCandidate, context: DecisionContext
    ) -> SemanticResponse:
        """Check fixture capabilities and policies; this is not Tiny-ME reasoning."""
        result = semantic.validate_countermeasure(strategy, context)
        return SemanticResponse(
            contract=SEMANTIC_CONTRACT,
            backend_kind="mock",
            backend=result.backend,
            request_sha256=digest(
                SemanticRequest(strategy=strategy, context=context).model_dump(mode="json")
            ),
            result=result,
        )

    @server.tool(
        annotations=ToolAnnotations(readOnlyHint=False, destructiveHint=False, idempotentHint=True)
    )
    def record_provenance(record: ProvenanceRecord) -> ProvenanceResponse:
        """Persist the JSON record in server SQLite and return a mock receipt, not a Fabric tx."""
        return ProvenanceResponse(
            contract=PROVENANCE_CONTRACT,
            backend_kind="mock",
            backend=provenance.backend,
            request_sha256=digest(ProvenanceRequest(record=record).model_dump(mode="json")),
            result=provenance.record_provenance(record),
        )

    return server


def main(argv=None):
    parser = argparse.ArgumentParser(description="Server MCP HTTP dei tool strategici mock")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8002)
    parser.add_argument("--data-dir", type=Path, default=Path("output/mcp-mock-store"))
    args = parser.parse_args(argv)
    if not 1 <= args.port <= 65535:
        parser.error("La porta deve essere compresa fra 1 e 65535")
    create_server(host=args.host, port=args.port, data_dir=args.data_dir).run(
        transport="streamable-http"
    )


if __name__ == "__main__":
    main()
