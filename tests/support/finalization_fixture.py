"""Synthetic shared finalization, for transport tests only; no real Fabric attestation."""

import json
from urllib.parse import quote

from thesis_agents.mcp.finalization_contracts import FinalizationDocument, raw_digest


def response_for(document_json, assurance):
    doc = FinalizationDocument.model_validate_json(document_json)
    fin = doc.finalization_id
    final_uri = f"urn:cti:recommendation:{fin}"
    activity = f"urn:cti:fixture:selection:{fin}"
    entities = [
        {
            "id": final_uri,
            "type": "prov:Entity",
            "attributes": {
                "document_sha256": raw_digest(document_json),
                "selected_strategy_id": doc.recommendation.selected_strategy_id,
                "outcome": doc.recommendation.outcome,
                "ranking_decision_id": doc.ranking_decision_id,
                "selection_policy": doc.selection_policy,
                "run_id": doc.run_id,
                "asset_id": doc.asset_id,
                "cve_id": doc.recommendation.cve_id,
                "tenant_id": doc.tenant_id,
                "ranking_graph_key": doc.ranking_graph_key,
                "action_execution": "not_performed",
            },
        }
    ]
    relations = [{"subject": final_uri, "predicate": "prov:wasGeneratedBy", "object": activity}]
    used = []
    for name, digest in doc.source_digests.items():
        uri = f"urn:cti:fixture:artifact:{name}"
        entities.append(
            {
                "id": uri,
                "type": "prov:Entity",
                "attributes": {
                    "artifact_name": name,
                    "sha256": digest,
                    "origin": "synthetic_fixture",
                },
            }
        )
        used.append(uri)
        relations.append({"subject": activity, "predicate": "prov:used", "object": uri})
    for row in doc.recommendation.candidates:
        attempt = row.validation
        uri = f"urn:cti:fixture:validation:{quote(attempt.strategy_id, safe='')}"
        entities.append(
            {
                "id": uri,
                "type": "prov:Entity",
                "attributes": {
                    "strategy_id": attempt.strategy_id,
                    "ontology_individual": attempt.ontology_individual,
                    "countermeasure_iri": attempt.request.countermeasure_iri,
                    "semantic_status": attempt.response.status,
                    "operational_status": attempt.response.operational.status,
                    "effective_status": attempt.response.effective_status,
                    "context_digest": attempt.response.operational.context_digest,
                    "origin": "backend_recorded_validation",
                },
            }
        )
        used.append(uri)
        relations.append({"subject": activity, "predicate": "prov:used", "object": uri})
    provenance = {
        "decisionId": doc.ranking_decision_id,
        "finalizationId": fin,
        "context": {"prov": "http://www.w3.org/ns/prov#"},
        "entities": entities,
        "activities": [{"id": activity, "type": "prov:Activity", "usedEntities": used}],
        "agents": [],
        "relations": relations,
        "slsaAssurance": assurance,
        "knowledgeSnapshotId": doc.knowledge_snapshot_id,
        "knowledgeSnapshotDigest": doc.knowledge_snapshot_digest,
    }
    raw_prov = json.dumps(provenance, ensure_ascii=False, separators=(",", ":"))
    return {
        "contract": "shared-finalization-response-v1",
        "record": {
            "contract": "shared-finalization-record-v1",
            "finalization_id": fin,
            "tenant_id": doc.tenant_id,
            "document_json": document_json,
            "document_sha256": raw_digest(document_json),
            "provenance_json": raw_prov,
            "provenance_sha256": raw_digest(raw_prov),
            "transaction_id": "fixture-tx-" + fin,
        },
        "commit": {
            "transaction_id": "fixture-tx-" + fin,
            "block_number": "42",
            "validation_code": 0,
            "successful": True,
        },
        "ledger_readback_verified": True,
        "verification_scope": "backend_reported_commit_and_readback",
        "deployment_verified": False,
        "action_execution": "not_performed",
    }
