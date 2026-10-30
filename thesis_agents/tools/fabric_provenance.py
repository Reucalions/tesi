"""Adapter Workforce per PROV-O/Fabric, separato dal contratto MCP storico."""

import hashlib
import json

from thesis_agents.mcp.client import digest
from thesis_agents.mcp.fabric_client import native_call
from thesis_agents.mcp.fabric_contracts import fabric_contracts
from thesis_agents.provenance import export_prov


def fabric_provenance_contracts():
    return {
        name: spec
        for name, spec in fabric_contracts().items()
        if name in ("record_provenance", "read_provenance")
    }


class FabricProvenanceTool:
    backend = "mcp-fablo-provenance-v1"

    def __init__(self, client, output_dir, *, channel, chaincode):
        self.client, self.output_dir = client, output_dir
        self.channel, self.chaincode = channel, chaincode

    def _validate(self, response, record):
        document = {"record": record.model_dump(mode="json"), "jsonld": export_prov(record)}
        stored = response.result
        try:
            raw = stored["document_json"]
            raw_valid = json.loads(raw) == document and hashlib.sha256(
                raw.encode()
            ).hexdigest() == digest(document)
        except (KeyError, TypeError, ValueError, AttributeError):
            raw_valid = False
        if (
            not raw_valid
            or response.channel != self.channel
            or response.chaincode != self.chaincode
            or stored.get("document") != document
            or stored.get("document_sha256") != digest(document)
            or stored.get("run_id") != record.run_id
            or not isinstance(stored.get("tx_id"), str)
            or not stored["tx_id"]
        ):
            raise ValueError("Fabric provenance does not match the run, document or ledger binding")
        return stored

    def record_provenance(self, record):
        written = native_call(
            self.client, "record_provenance", record=record.model_dump(mode="json")
        )
        if written.verification != "peer-readback":
            raise ValueError("Fabric provenance requires verified server readback")
        stored = self._validate(written, record)
        read = native_call(self.client, "read_provenance", run_id=record.run_id)
        if self._validate(read, record) != stored:
            raise ValueError("Fabric provenance client readback differs from the write response")
        receipt = {
            "run_id": record.run_id,
            "stored": True,
            "backend": self.backend,
            "record_sha256": digest(record.model_dump(mode="json")),
            "jsonld_sha256": digest(export_prov(record)),
            "document_sha256": stored["document_sha256"],
            "channel": self.channel,
            "chaincode": self.chaincode,
            "tx_id": stored["tx_id"],
            "receipt_id": f"fabric:{stored['tx_id']}",
            "storage_kind": "fabric-world-state",
            "ledger_status": "peer_readback_verified",
            "block_commit_verified": False,
        }
        for filename, payload in (
            ("provenance.jsonld", export_prov(record)),
            ("fabric_provenance_snapshot.json", read.model_dump(mode="json")),
            ("provenance_receipt.json", receipt),
        ):
            path = self.output_dir / filename
            if path.exists():
                if json.loads(path.read_text()) != payload:
                    raise ValueError("Fabric provenance artifacts are immutable")
            else:
                with path.open("x") as stream:
                    stream.write(json.dumps(payload, indent=2) + "\n")
        return receipt

    def verify_export(self, record):
        from thesis_agents.mcp.fabric_contracts import FabricResponse

        response = FabricResponse.model_validate_json(
            (self.output_dir / "fabric_provenance_snapshot.json").read_text()
        )
        stored = self._validate(response, record)
        document = json.loads((self.output_dir / "provenance.jsonld").read_text())
        receipt = json.loads((self.output_dir / "provenance_receipt.json").read_text())
        if (
            response.operation != "read_provenance"
            or response.verification != "peer-query"
            or response.request_sha256 != digest({"run_id": record.run_id})
            or document != export_prov(record)
            or receipt.get("run_id") != record.run_id
            or receipt.get("record_sha256") != digest(record.model_dump(mode="json"))
            or receipt.get("jsonld_sha256") != digest(document)
            or receipt.get("document_sha256") != stored["document_sha256"]
            or receipt.get("tx_id") != stored["tx_id"]
            or receipt.get("stored") is not True
            or receipt.get("receipt_id") != f"fabric:{stored['tx_id']}"
            or receipt.get("backend") != self.backend
            or receipt.get("channel") != self.channel
            or receipt.get("chaincode") != self.chaincode
            or receipt.get("storage_kind") != "fabric-world-state"
            or receipt.get("ledger_status") != "peer_readback_verified"
            or receipt.get("block_commit_verified") is not False
        ):
            raise ValueError("Fabric provenance export or receipt differs from validated state")
        return receipt
