"""Archivio remoto verificato tramite rilettura; nessun accesso ai file del server."""

import json

from thesis_agents.mcp.client import digest
from thesis_agents.mcp.contracts import PROVENANCE_TOOL, ProvenanceRequest, ProvenanceResponse
from thesis_agents.mcp.evidence_strategic_contracts import (
    READ_TOOL,
    ReadProvenanceRequest,
    ReadProvenanceResponse,
)
from thesis_agents.provenance import export_prov
from thesis_agents.tools.strategic_mcp import MCPRankingTool, strategic_contracts, validate_response


class EmptyEvidenceRankingTool(MCPRankingTool):
    def rank_graph(self, graph):
        if graph.arguments or graph.relations:
            raise ValueError("Nonempty graphs require a validated BWAF mapping and service")
        result = super().rank_graph(graph)
        if result.backend != "empty-strategy-gate-v1" or result.ranking:
            raise ValueError("Evidence gate must explicitly abstain on an empty strategy set")
        return result


def evidence_provenance_contracts():
    return {
        **strategic_contracts("provenance"),
        READ_TOOL: (
            ReadProvenanceRequest.model_json_schema(),
            ReadProvenanceResponse.model_json_schema(),
        ),
    }


class EvidenceProvenanceTool:
    backend = "mcp-artifact-jsonld-store-v1"

    def __init__(self, client, output_dir):
        self.client, self.output_dir = client, output_dir

    def record_provenance(self, record):
        arguments = ProvenanceRequest(record=record).model_dump(mode="json")

        def parse_receipt(payload):
            response = ProvenanceResponse.model_validate(payload)
            validate_response(response, self.client, arguments)
            receipt = response.result
            if (
                receipt.backend != "artifact-jsonld-store-v1"
                or not receipt.stored
                or receipt.run_id != record.run_id
                or receipt.record_sha256 != digest(record.model_dump(mode="json"))
            ):
                raise ValueError("Invalid artifact-store receipt")
            return receipt

        receipt = self.client.call_tool(PROVENANCE_TOOL, arguments, parse_receipt)
        request = ReadProvenanceRequest(run_id=record.run_id).model_dump(mode="json")

        def parse_read(payload):
            result = ReadProvenanceResponse.model_validate(payload)
            if (
                result.request_sha256 != digest(request)
                or result.record != record
                or result.record_sha256 != receipt.record_sha256
                or result.jsonld != export_prov(record)
                or result.jsonld_sha256 != digest(result.jsonld)
            ):
                raise ValueError("Remote provenance readback differs from submitted artifacts")
            return result

        stored = self.client.call_tool(READ_TOOL, request, parse_read)
        result = {
            **receipt.model_dump(mode="json"),
            "storage_kind": stored.storage_kind,
            "ledger_status": stored.ledger_status,
            "jsonld_sha256": stored.jsonld_sha256,
        }
        for filename, payload in (
            ("provenance.jsonld", stored.jsonld),
            ("provenance_receipt.json", result),
        ):
            path = self.output_dir / filename
            if path.exists():
                if json.loads(path.read_text()) != payload:
                    raise ValueError("Local provenance export and receipt are immutable")
            else:
                with path.open("x") as stream:
                    stream.write(json.dumps(payload, indent=2) + "\n")
        return result

    def verify_export(self, record):
        document = json.loads((self.output_dir / "provenance.jsonld").read_text())
        receipt = json.loads((self.output_dir / "provenance_receipt.json").read_text())
        if (
            document != export_prov(record)
            or receipt.get("jsonld_sha256") != digest(document)
            or receipt.get("record_sha256") != digest(record.model_dump(mode="json"))
            or receipt.get("run_id") != record.run_id
            or receipt.get("ledger_status") != "not_submitted"
            or receipt.get("storage_kind") != "artifact-files"
        ):
            raise ValueError("Provenance export or receipt differs from validated artifacts")
        return receipt
