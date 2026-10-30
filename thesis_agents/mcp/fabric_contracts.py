"""Contratti nativi del backend Fabric; nessuna conversione implicita del grafo MVP."""

from typing import Annotated, Literal

from pydantic import Field, StrictBool, model_validator

from thesis_agents.schemas import ProvenanceRecord
from thesis_agents.schemas.base import Identifier, Message, Text, require_unique

SHA256 = Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
OntologyText = Annotated[str, Field(min_length=1, max_length=2_000_000)]


class NativeNode(Message):
    id: Text
    type: Text


class NativeEdge(Message):
    # Nomi identici a GraphInput del chaincode originale.
    from_: Text = Field(alias="from")
    to: Text


class NativeGraph(Message):
    nodes: list[NativeNode] = Field(min_length=1, max_length=1000)
    edges: list[NativeEdge] = Field(min_length=1, max_length=10000)

    @model_validator(mode="after")
    def references(self):
        ids = [node.id for node in self.nodes]
        require_unique(ids, "native node IDs")
        pairs = [(edge.from_, edge.to) for edge in self.edges]
        if len(pairs) != len(set(pairs)):
            raise ValueError("Duplicate native edges")
        if any(a not in ids or b not in ids or a == b for a, b in pairs):
            raise ValueError("Invalid native edge")
        if not any(node.type == "strategy" for node in self.nodes):
            raise ValueError("A native ranking graph requires strategies")
        return self


class GraphKey(Message):
    graph_id: Identifier


class StoreGraphRequest(GraphKey):
    graph: NativeGraph


class AnalyzeOntologyRequest(Message):
    ontology_key: Identifier
    ontology: OntologyText
    resource: Text
    request: Text

    def content_key(self):
        from thesis_agents.mcp.client import digest

        return "analysis:" + digest(
            {"ontology": self.ontology, "resource": self.resource, "request": self.request}
        )


class OntologyKey(Message):
    ontology_key: Identifier


class ReasonerResult(Message):
    ontologyKey: Text
    isCoherent: StrictBool
    tbox: str
    abox: str
    abductionResult: str
    bonusResult: str
    contractionResult: str
    details: str
    timestamp: Annotated[int, Field(ge=0, strict=True)]


class RecordProvenanceRequest(Message):
    record: ProvenanceRecord


class ProvenanceKey(Message):
    run_id: Identifier


class FabricResponse(Message):
    contract: Literal["fabric-native-v1"] = "fabric-native-v1"
    backend_kind: Literal["real"] = "real"
    backend: Literal["fablo-fabric-native-v1"] = "fablo-fabric-native-v1"
    request_sha256: SHA256
    operation: Literal[
        "store_graph",
        "rank_graph",
        "get_graph",
        "get_rank_result",
        "get_annotated_graph",
        "analyze_ontology",
        "get_reasoner_result",
        "record_provenance",
        "read_provenance",
    ]
    channel: Text
    chaincode: Text
    # Query eseguita sul peer: non è una verifica indipendente del commit sul blocco.
    verification: Literal["peer-readback", "peer-query"]
    result: dict


FABRIC_TOOLS = {
    "store_graph": StoreGraphRequest,
    "rank_graph": GraphKey,
    "get_graph": GraphKey,
    "get_rank_result": GraphKey,
    "get_annotated_graph": GraphKey,
    "analyze_ontology": AnalyzeOntologyRequest,
    "get_reasoner_result": OntologyKey,
    "record_provenance": RecordProvenanceRequest,
    "read_provenance": ProvenanceKey,
}


def fabric_contracts():
    return {
        name: (request.model_json_schema(), FabricResponse.model_json_schema())
        for name, request in FABRIC_TOOLS.items()
    }
