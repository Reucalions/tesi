"""MCP HTTP → Fablo REST → chaincode originali e chaincode PROV-O dedicato."""

import argparse
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from thesis_agents.mcp.fabric_contracts import (
    AnalyzeOntologyRequest,
    FabricResponse,
    GraphKey,
    NativeGraph,
    OntologyKey,
    OntologyText,
    ProvenanceKey,
    RecordProvenanceRequest,
    StoreGraphRequest,
)
from thesis_agents.schemas import ProvenanceRecord
from thesis_agents.schemas.base import Identifier, Text

from .fablo import FabloClient, FabloSettings
from .fabric import FabricGateway


def create_server(gateway: FabricGateway, *, port=8008):
    server = FastMCP(
        "fabric-native-gateway",
        host="127.0.0.1",
        port=port,
        json_response=True,
        log_level="WARNING",
    )

    @server.tool()
    def store_graph(graph_id: Identifier, graph: NativeGraph) -> FabricResponse:
        """Store the native ontology graph and verify its ledger readback."""
        return gateway.store_graph(StoreGraphRequest(graph_id=graph_id, graph=graph))

    @server.tool()
    def rank_graph(graph_id: Identifier) -> FabricResponse:
        """Invoke the original RankGraph chaincode and read back both results."""
        return gateway.rank_graph(GraphKey(graph_id=graph_id))

    @server.tool()
    def get_graph(graph_id: Identifier) -> FabricResponse:
        """Read the original native graph from Fabric."""
        return gateway.get_graph(GraphKey(graph_id=graph_id))

    @server.tool()
    def get_rank_result(graph_id: Identifier) -> FabricResponse:
        """Retrieve native scores and explanations without clamping or normalization."""
        return gateway.get_rank_result(GraphKey(graph_id=graph_id))

    @server.tool()
    def get_annotated_graph(graph_id: Identifier) -> FabricResponse:
        """Retrieve the ontology engine's annotated graph."""
        return gateway.get_annotated_graph(GraphKey(graph_id=graph_id))

    @server.tool()
    def analyze_ontology(
        ontology_key: Identifier,
        ontology: OntologyText,
        resource: Text,
        request: Text,
    ) -> FabricResponse:
        """Run Tiny-ME abduction, bonus and contraction; does not accept a mitigation."""
        return gateway.analyze_ontology(
            AnalyzeOntologyRequest(
                ontology_key=ontology_key,
                ontology=ontology,
                resource=resource,
                request=request,
            )
        )

    @server.tool()
    def get_reasoner_result(ontology_key: Identifier) -> FabricResponse:
        """Read back the original Tiny-ME result stored by AnalyzeOntology."""
        return gateway.get_reasoner_result(OntologyKey(ontology_key=ontology_key))

    @server.tool()
    def record_provenance(record: ProvenanceRecord) -> FabricResponse:
        """Store the record and PROV-O bundle in the dedicated chaincode, then read it."""
        return gateway.record_provenance(RecordProvenanceRequest(record=record))

    @server.tool()
    def read_provenance(run_id: Identifier) -> FabricResponse:
        """Retrieve PROV-O, its digest and the transaction ID from the provenance chaincode."""
        return gateway.read_provenance(ProvenanceKey(run_id=run_id))

    return server


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--port", default=8008, type=int)
    args = parser.parse_args()
    settings = FabloSettings.model_validate_json(args.config.read_text())
    client = FabloClient(settings)
    try:
        create_server(FabricGateway(client), port=args.port).run(transport="streamable-http")
    finally:
        client.close()


if __name__ == "__main__":
    main()
