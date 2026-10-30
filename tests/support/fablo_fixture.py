"""HTTP Fablo simulato per i test; nessun algoritmo di dominio reale."""

import base64
import copy
import json

import httpx

from thesis_agents.mcp.client import digest


class SimulatedFablo:
    """Fixture di trasporto; punteggi e stringhe Tiny-ME sono dati sintetici."""

    def __init__(self):
        self.values, self.provenance, self.reasoning, self.calls = {}, {}, {}, []
        self.fault = None

    def __call__(self, request):
        body = json.loads(request.content)
        self.calls.append((request.url.path, body))
        if request.url.path == "/user/enroll":
            assert body == {"id": "admin", "secret": "test-only-secret"}
            return httpx.Response(200, json={"token": "test-only-token"})
        assert request.headers["Authorization"] == "Bearer test-only-token"
        method, args = body["method"], body["args"]
        if self.fault == "http":
            return httpx.Response(500, json={"secret": "do-not-expose"})
        if self.fault == "accepted":
            return httpx.Response(202, json={"response": {"success": "OK"}})
        if self.fault == "chaincode-error":
            return httpx.Response(200, json={"response": {"error": "NOT_FOUND"}})
        if method.endswith(":Get"):
            result = (
                {"success": json.dumps(self.values[args[0]])}
                if args[0] in self.values
                else {"error": "NOT_FOUND"}
            )
        elif method.endswith(":StoreGraph"):
            self.values[args[0]] = json.loads(args[1])
            if self.fault == "tampered-store":
                self.values[args[0]]["nodes"][0]["id"] = "other"
            result = {"success": "OK"}
        elif method.endswith(":RankGraph"):
            self.values[args[0] + "_rank"] = [
                {"name": "Upgrade", "score": 1.25, "explanation": {"favor": [], "against": []}}
            ]
            self.values[args[0] + "_annotated_graph"] = {
                "nodes": [
                    {"data": {"id": 1, "label": "CVE_assertion"}},
                    {"data": {"id": 2, "label": "Upgrade"}},
                ],
                "edges": [{"data": {"source": 1, "target": 2, "label": 0.7}}],
            }
            if self.fault == "wrong-ranking":
                self.values[args[0] + "_rank"][0]["name"] = "Unrelated"
            result = {"success": "OK"}
        elif method == "AnalyzeOntology":
            assert args[3:] == ["true", "true", "true"]
            content = base64.b64decode(base64.b64decode(body["transient"]["ontology"]))
            assert content == b"Ontology(test-transport-only)"
            result = {
                "ontologyKey": args[0],
                "isCoherent": True,
                "tbox": "fixture-tbox",
                "abox": "fixture-abox",
                "abductionResult": "fixture-abduction",
                "bonusResult": "fixture-bonus",
                "contractionResult": "fixture-contraction",
                "details": "synthetic fixture, no reasoner",
                "timestamp": 123,
            }
            self.reasoning[args[0]] = copy.deepcopy(result)
            if self.fault == "tampered-reasoning":
                self.reasoning[args[0]]["bonusResult"] = "other"
            if self.fault == "missing-reasoning":
                result["abductionResult"] = ""
        elif method == "ReadReasonerResult":
            result = self.reasoning[args[0]]
        elif method == "StoreProvenance":
            document = json.loads(args[1])
            result = {
                "run_id": args[0],
                "document_json": args[1],
                "document_sha256": digest(document),
                "tx_id": "synthetic-tx",
            }
            self.provenance[args[0]] = result
            if self.fault == "tampered-provenance":
                self.provenance[args[0]]["document_sha256"] = "0" * 64
        elif method == "GetProvenance":
            result = self.provenance[args[0]]
        else:
            raise AssertionError(method)
        return httpx.Response(200, json={"response": result})
