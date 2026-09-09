from pathlib import Path

from thesis_agents.schemas import ProvenanceRecord


class MockProvenanceTool:
    """Local JSON receipt; no ledger transaction or PROV-O conformance claim."""

    def __init__(self, output_dir: Path):
        self.output_dir = output_dir

    def record_provenance(self, record: ProvenanceRecord) -> dict:
        path = self.output_dir / "provenance.json"
        payload = record.model_dump_json(indent=2) + "\n"
        if path.exists():
            if path.read_text() != payload:
                raise ValueError("A different provenance record already exists")
        else:
            with path.open("x", encoding="utf-8") as stream:
                stream.write(payload)
        return {"run_id": record.run_id, "backend": record.backend, "stored": True}
