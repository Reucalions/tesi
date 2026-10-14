"""Adapter dei tool strategici: invocano MCP senza eseguire i backend in locale."""

from pathlib import Path

from thesis_agents.mcp.client import MCPClient, digest
from thesis_agents.mcp.contracts import (
    PROVENANCE_TOOL,
    RANKING_TOOL,
    SEMANTIC_TOOL,
    ProvenanceRequest,
    ProvenanceResponse,
    RankingRequest,
    RankingResponse,
    SemanticRequest,
    SemanticResponse,
)
from thesis_agents.schemas import (
    ArgumentationGraph,
    CountermeasureCandidate,
    DecisionContext,
    ProvenanceRecord,
    RankingResult,
    SemanticValidationResult,
)


def strategic_contracts(service: str) -> dict:
    tool, request, response = {
        "ranking": (RANKING_TOOL, RankingRequest, RankingResponse),
        "semantic": (SEMANTIC_TOOL, SemanticRequest, SemanticResponse),
        "provenance": (PROVENANCE_TOOL, ProvenanceRequest, ProvenanceResponse),
    }[service]
    return {tool: (request.model_json_schema(), response.model_json_schema())}


def validate_response(response, client, arguments):
    if response.backend_kind != client.settings.expected_kind:
        raise ValueError("Il server dichiara un tipo di backend diverso da quello richiesto")
    if response.request_sha256 != digest(arguments):
        raise ValueError("La risposta non corrisponde alla richiesta MCP")
    if response.result.backend != response.backend:
        raise ValueError("Identità del backend incoerente nella risposta MCP")


class MCPRankingTool:
    def __init__(self, client: MCPClient):
        self.client = client

    def rank_graph(self, graph: ArgumentationGraph) -> RankingResult:
        arguments = RankingRequest(graph=graph).model_dump(mode="json")

        def parse(payload):
            response = RankingResponse.model_validate(payload)
            validate_response(response, self.client, arguments)
            result = response.result
            ids = {node.strategy_id for node in graph.arguments if node.kind == "strategy"}
            if result.graph_id != graph.id or {r.strategy_id for r in result.ranking} != ids:
                raise ValueError("Ranking riferito a un altro grafo o insieme di strategie")
            return result

        return self.client.call_tool(RANKING_TOOL, arguments, parse)


class MCPSemanticTool:
    def __init__(self, client: MCPClient):
        self.client = client

    def validate_countermeasure(
        self, strategy: CountermeasureCandidate, context: DecisionContext
    ) -> SemanticValidationResult:
        arguments = SemanticRequest(strategy=strategy, context=context).model_dump(mode="json")

        def parse(payload):
            response = SemanticResponse.model_validate(payload)
            validate_response(response, self.client, arguments)
            if response.result.strategy_id != strategy.id:
                raise ValueError("Validazione riferita a un'altra strategia")
            return response.result

        return self.client.call_tool(SEMANTIC_TOOL, arguments, parse)


class MCPProvenanceTool:
    def __init__(self, client: MCPClient, receipt_path: Path):
        self.client = client
        self.receipt_path = receipt_path
        # Il record descrive il canale configurato; la ricevuta identifica il servizio.
        self.backend = f"mcp-provenance-{client.settings.expected_kind}-v1"

    def record_provenance(self, record: ProvenanceRecord) -> dict:
        arguments = ProvenanceRequest(record=record).model_dump(mode="json")

        def parse(payload):
            response = ProvenanceResponse.model_validate(payload)
            validate_response(response, self.client, arguments)
            receipt = response.result
            if (
                not receipt.stored
                or receipt.run_id != record.run_id
                or receipt.record_sha256 != digest(arguments["record"])
            ):
                raise ValueError("Ricevuta non riferita al record inviato o persistenza fallita")
            return receipt

        receipt = self.client.call_tool(PROVENANCE_TOOL, arguments, parse)
        # Sidecar separato: il documento inviato non può contenere la propria ricevuta.
        payload = receipt.model_dump_json(indent=2) + "\n"
        if self.receipt_path.exists():
            if self.receipt_path.read_text(encoding="utf-8") != payload:
                raise ValueError("Esiste già una ricevuta di provenienza differente")
        else:
            with self.receipt_path.open("x", encoding="utf-8") as stream:
                stream.write(payload)
        return receipt.model_dump(mode="json")
