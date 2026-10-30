"""Operazioni native Fabric con rilettura; nessun ranking o reasoner sostitutivo."""

import base64
import hashlib
import json
import math
from threading import RLock

from thesis_agents.mcp.client import digest
from thesis_agents.mcp.fabric_contracts import (
    AnalyzeOntologyRequest,
    FabricResponse,
    GraphKey,
    NativeGraph,
    OntologyKey,
    ProvenanceKey,
    ReasonerResult,
    RecordProvenanceRequest,
    StoreGraphRequest,
)
from thesis_agents.provenance import export_prov

from .fablo import FabloError


def json_value(payload):
    value = payload.get("success")
    if not isinstance(value, str) or value in ("OK", "NOT_FOUND"):
        raise FabloError("Ledger value not found or not serialized JSON")
    try:
        return json.loads(value)
    except ValueError:
        raise FabloError("Ledger value is not JSON") from None


def validate_ranking(ranking, graph):
    strategies = {node.id for node in graph.nodes if node.type == "strategy"}
    if not isinstance(ranking, list) or not ranking:
        raise FabloError("Native ranking must contain every strategy")
    names = []
    for entry in ranking:
        if not isinstance(entry, dict) or not isinstance(entry.get("name"), str):
            raise FabloError("Invalid native strategy entry")
        score = entry.get("score")
        if (
            isinstance(score, bool)
            or not isinstance(score, (float, int))
            or not math.isfinite(score)
        ):
            raise FabloError("Native score must be finite; no normalization is applied")
        names.append(entry["name"])
    if len(names) != len(set(names)) or set(names) != strategies:
        raise FabloError("Native ranking differs from stored strategies")
    # Conserva spiegazioni, ordine e scala del motore originale.
    return ranking


def validate_annotated(graph):
    if not isinstance(graph, dict) or set(graph) != {"nodes", "edges"}:
        raise FabloError("Invalid annotated graph")
    try:
        ids = [node["data"]["id"] for node in graph["nodes"]]
        if (
            not ids
            or len(ids) != len(set(ids))
            or any(isinstance(value, bool) or not isinstance(value, int) for value in ids)
            or any(not isinstance(node["data"]["label"], str) for node in graph["nodes"])
            or not graph["edges"]
        ):
            raise ValueError
        for edge in graph["edges"]:
            data = edge["data"]
            if data["source"] not in ids or data["target"] not in ids:
                raise ValueError
            if isinstance(data["label"], bool) or not math.isfinite(data["label"]):
                raise ValueError
    except (KeyError, TypeError, ValueError):
        raise FabloError("Invalid annotated graph references or weights") from None
    return graph


class FabricGateway:
    def __init__(self, client):
        self.client = client
        self.settings = client.settings
        # Serializza i cicli scrittura/rilettura di questo processo.
        self.lock = RLock()

    def response(self, operation, request, chaincode, result, *, written=False):
        return FabricResponse(
            operation=operation,
            request_sha256=digest(request.model_dump(mode="json", by_alias=True)),
            channel=self.settings.channel,
            chaincode=chaincode,
            verification="peer-readback" if written else "peer-query",
            result=result,
        )

    def _graph(self, graph_id, suffix=""):
        payload = self.client.call(
            "query",
            self.settings.argumentation_chaincode,
            "ArgumentationContract:Get",
            [graph_id + suffix],
        )
        return json_value(payload)

    def store_graph(self, request: StoreGraphRequest):
        graph = request.graph.model_dump(mode="json", by_alias=True)
        with self.lock:
            # ID content-addressed: il caller non può sovrascrivere uno stesso caso
            # con un grafo diverso. Il chaincode storico rimane invariato.
            expected = f"graph:{digest(graph)}"
            if request.graph_id != expected:
                raise ValueError("Native graph_id must be graph:<canonical graph SHA-256>")
            existing = self.client.call(
                "query",
                self.settings.argumentation_chaincode,
                "ArgumentationContract:Get",
                [request.graph_id],
                allow_missing=True,
            )
            if existing == {"error": "NOT_FOUND"}:
                result = self.client.call(
                    "invoke",
                    self.settings.argumentation_chaincode,
                    "ArgumentationContract:StoreGraph",
                    [request.graph_id, json.dumps(graph, ensure_ascii=False)],
                )
                if result != {"success": "OK"}:
                    raise FabloError("StoreGraph did not acknowledge persistence")
                stored = self._graph(request.graph_id)
            else:
                stored = json_value(existing)
            if stored != graph:
                raise FabloError("Ledger key already contains a different graph")
        return self.response(
            "store_graph",
            request,
            self.settings.argumentation_chaincode,
            {"graph_id": request.graph_id, "graph": stored},
            written=True,
        )

    def get_graph(self, request: GraphKey):
        graph = NativeGraph.model_validate(self._graph(request.graph_id))
        data = graph.model_dump(mode="json", by_alias=True)
        if request.graph_id != f"graph:{digest(data)}":
            raise FabloError("Stored graph digest differs from its key")
        return self.response(
            "get_graph",
            request,
            self.settings.argumentation_chaincode,
            {"graph_id": request.graph_id, "graph": data},
        )

    def rank_graph(self, request: GraphKey):
        with self.lock:
            self.get_graph(request)
            result = self.client.call(
                "invoke",
                self.settings.argumentation_chaincode,
                "ArgumentationContract:RankGraph",
                [request.graph_id],
            )
            if result != {"success": "OK"}:
                raise FabloError("RankGraph did not acknowledge computation")
            ranking = self.get_rank_result(request).result["ranking"]
            annotated = self.get_annotated_graph(request).result["graph"]
        return self.response(
            "rank_graph",
            request,
            self.settings.argumentation_chaincode,
            {
                "graph_id": request.graph_id,
                "ranking": ranking,
                "annotated_graph_sha256": digest(annotated),
            },
            written=True,
        )

    def get_rank_result(self, request: GraphKey):
        graph = NativeGraph.model_validate(self.get_graph(request).result["graph"])
        ranking = validate_ranking(self._graph(request.graph_id, "_rank"), graph)
        return self.response(
            "get_rank_result",
            request,
            self.settings.argumentation_chaincode,
            {"graph_id": request.graph_id, "ranking": ranking},
        )

    def get_annotated_graph(self, request: GraphKey):
        self.get_graph(request)
        graph = validate_annotated(self._graph(request.graph_id, "_annotated_graph"))
        return self.response(
            "get_annotated_graph",
            request,
            self.settings.argumentation_chaincode,
            {"graph_id": request.graph_id, "graph": graph},
        )

    def analyze_ontology(self, request: AnalyzeOntologyRequest):
        if request.ontology_key != request.content_key():
            raise ValueError("Ontology analysis key must bind its content and both individuals")
        with self.lock:
            # AnalyzeOntology richiede una seconda codifica Base64: REST decodifica
            # il transient e il chaincode decodifica nuovamente il suo contenuto.
            ontology = base64.b64encode(request.ontology.encode())
            transient = {"ontology": base64.b64encode(ontology).decode()}
            result = self.client.call(
                "invoke",
                self.settings.semantic_chaincode,
                "AnalyzeOntology",
                [request.ontology_key, request.resource, request.request, "true", "true", "true"],
                transient=transient,
            )
            parsed = ReasonerResult.model_validate(result)
            if parsed.ontologyKey != request.ontology_key:
                raise FabloError("Reasoner result belongs to another ontology")
            if parsed.isCoherent and not all(
                (parsed.abductionResult, parsed.bonusResult, parsed.contractionResult)
            ):
                raise FabloError("A requested Tiny-ME reasoning result is missing")
            reread = self.get_reasoner_result(OntologyKey(ontology_key=request.ontology_key))
            if reread.result != parsed.model_dump(mode="json"):
                raise FabloError("Tiny-ME ledger readback differs from invocation")
        return self.response(
            "analyze_ontology",
            request,
            self.settings.semantic_chaincode,
            reread.result,
            written=True,
        )

    def get_reasoner_result(self, request: OntologyKey):
        result = self.client.call(
            "query", self.settings.semantic_chaincode, "ReadReasonerResult", [request.ontology_key]
        )
        parsed = ReasonerResult.model_validate(result)
        if parsed.ontologyKey != request.ontology_key:
            raise FabloError("Tiny-ME result refers to another ontology key")
        return self.response(
            "get_reasoner_result",
            request,
            self.settings.semantic_chaincode,
            parsed.model_dump(mode="json"),
        )

    def record_provenance(self, request: RecordProvenanceRequest):
        document = {
            "record": request.record.model_dump(mode="json"),
            "jsonld": export_prov(request.record),
        }
        with self.lock:
            self.client.call(
                "invoke",
                self.settings.provenance_chaincode,
                "StoreProvenance",
                [
                    request.record.run_id,
                    json.dumps(
                        document,
                        sort_keys=True,
                        ensure_ascii=False,
                        separators=(",", ":"),
                        allow_nan=False,
                    ),
                ],
            )
            reread = self.read_provenance(ProvenanceKey(run_id=request.record.run_id))
            if reread.result["document"] != document:
                raise FabloError("Provenance ledger readback differs from submitted PROV-O")
        return self.response(
            "record_provenance",
            request,
            self.settings.provenance_chaincode,
            reread.result,
            written=True,
        )

    def read_provenance(self, request: ProvenanceKey):
        result = self.client.call(
            "query", self.settings.provenance_chaincode, "GetProvenance", [request.run_id]
        )
        if result.get("run_id") != request.run_id or not result.get("tx_id"):
            raise FabloError("Provenance ledger identity or transaction reference missing")
        try:
            document = json.loads(result["document_json"])
            record = RecordProvenanceRequest.model_validate({"record": document["record"]}).record
            if (
                record.run_id != request.run_id
                or document["jsonld"] != export_prov(record)
                or result["document_sha256"] != digest(document)
                or hashlib.sha256(result["document_json"].encode()).hexdigest()
                != result["document_sha256"]
            ):
                raise ValueError
        except (KeyError, TypeError, ValueError):
            raise FabloError("Stored provenance document or digest is inconsistent") from None
        result = {**result, "document": document}
        return self.response("read_provenance", request, self.settings.provenance_chaincode, result)
