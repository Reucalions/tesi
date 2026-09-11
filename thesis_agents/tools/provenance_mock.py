# Backend di persistenza della provenienza per il prototipo senza Fabric.
# Riceve un record già costruito da ArtifactSession: non calcola hash o dipendenze,
# ma ne serializza il contenuto e conferma che il file locale sia stato salvato.
from pathlib import Path

from thesis_agents.schemas import ProvenanceRecord


class MockProvenanceTool:
    """Local JSON receipt; no ledger transaction or PROV-O conformance claim."""

    def __init__(self, output_dir: Path):
        # La sessione crea e verifica la directory prima di costruire il mock.
        self.output_dir = output_dir

    def record_provenance(self, record: ProvenanceRecord) -> dict:
        # Il nome del file è fisso dentro la directory del run. Indentazione e newline
        # rendono l'output leggibile e permettono il confronto esatto durante un retry.
        path = self.output_dir / "provenance.json"
        payload = record.model_dump_json(indent=2) + "\n"
        if path.exists():
            # Idempotenza: stesso contenuto significa pubblicazione già completata;
            # contenuto diverso indica un conflitto e non deve essere sovrascritto.
            if path.read_text() != payload:
                raise ValueError("A different provenance record already exists")
        else:
            # La creazione esclusiva «x» evita sovrascritture anche se il file viene
            # creato dopo il controllo exists e prima di questa apertura.
            with path.open("x", encoding="utf-8") as stream:
                stream.write(payload)
        # Ricevuta minimale restituita all'agente: stored non implica un commit blockchain.
        return {"run_id": record.run_id, "backend": record.backend, "stored": True}
