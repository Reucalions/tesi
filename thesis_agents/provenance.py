"""Export deterministico PROV-O JSON-LD; nessuna attestazione o transazione Fabric."""

import re
from urllib.parse import quote

from thesis_agents.schemas import ProvenanceRecord
from thesis_agents.schemas.base import require_unique


def export_prov(record: ProvenanceRecord) -> dict:
    entities = {e.id for e in record.entities}
    agents = set(record.agents)
    require_unique([e.id for e in record.entities], "provenance entity IDs")
    require_unique([a.id for a in record.activities], "provenance activity IDs")
    require_unique(record.agents, "provenance agents")
    for entity in record.entities:
        if not re.fullmatch(r"[0-9a-f]{64}", entity.sha256):
            raise ValueError("PROV export requires SHA-256 hashes")
    for activity in record.activities:
        if activity.agent not in agents or not set(activity.used + activity.generated) <= entities:
            raise ValueError("PROV activity refers to an unknown agent or entity")
        require_unique(activity.used, "used entities")
        require_unique(activity.generated, "generated entities")

    base = f"urn:tesi:run:{quote(record.run_id, safe='')}"

    def ref(kind, value):
        return {"@id": f"{base}:{kind}:{quote(value, safe='')}"}

    nodes = [
        {**ref("agent", a), "@type": "prov:SoftwareAgent", "tesi:role": a}
        for a in sorted(record.agents)
    ]
    for entity in sorted(record.entities, key=lambda e: e.id):
        generated = [a for a in record.activities if entity.id in a.generated]
        nodes.append(
            {
                **ref("entity", entity.id),
                "@type": "prov:Entity",
                "tesi:filename": entity.filename,
                "tesi:sha256": entity.sha256,
                "prov:wasGeneratedBy": [ref("activity", a.id) for a in generated],
                "prov:wasAttributedTo": [
                    ref("agent", a) for a in sorted({g.agent for g in generated})
                ],
                "prov:wasDerivedFrom": [
                    ref("entity", used) for used in sorted({u for a in generated for u in a.used})
                ],
            }
        )
    for activity in sorted(record.activities, key=lambda a: a.id):
        nodes.append(
            {
                **ref("activity", activity.id),
                "@type": "prov:Activity",
                "prov:used": [ref("entity", e) for e in activity.used],
                "prov:generated": [ref("entity", e) for e in activity.generated],
                "prov:wasAssociatedWith": ref("agent", activity.agent),
            }
        )
    return {
        "@context": {"prov": "http://www.w3.org/ns/prov#", "tesi": "urn:tesi:vocab:"},
        "@id": base,
        "@type": "prov:Bundle",
        "tesi:mode": record.mode,
        "tesi:runCreatedAt": record.created_at,
        "tesi:inferenceModel": record.model,
        "tesi:ledgerStatus": "not_submitted",
        "@graph": nodes,
    }
