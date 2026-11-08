"""Immutable recommendation registration over the existing shared SaaS/MCP service."""

import hashlib
import json
from importlib.resources import files
from typing import Annotated, Literal

from pydantic import Field, model_validator

from thesis_agents.mcp.shared_contracts import Digest, SharedProvenance, WireModel
from thesis_agents.schemas.base import Text
from thesis_agents.strategic.selection_contracts import CVERecommendation

SOURCES = (
    "runtime_evidence",
    "vulnerability_report",
    "candidate_strategies",
    "canonical_preparation",
    "native_strategic_ranking",
    "native_strategic_validation",
    "validation_profile",
    "native_strategic_recommendation",
)
FinalizationID = Annotated[str, Field(pattern=r"^FIN_[0-9a-f]{64}$")]


def raw_digest(raw: str) -> str:
    return "sha256:" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


def strict_json(raw: str):
    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise ValueError("Duplicate JSON field")
            result[key] = value
        return result

    if not isinstance(raw, str) or not raw or len(raw.encode("utf-8")) > 4 * 1024 * 1024:
        raise ValueError("Bounded UTF-8 JSON required")
    return json.loads(
        raw,
        object_pairs_hook=pairs,
        parse_constant=lambda v: (_ for _ in ()).throw(ValueError("Nonfinite JSON number")),
    )


class FinalizationDocument(WireModel):
    contract: Literal["shared-recommendation-finalization-v1"] = (
        "shared-recommendation-finalization-v1"
    )
    run_id: Text
    asset_id: Text
    tenant_id: Text
    ranking_decision_id: Text
    ranking_graph_key: Text
    knowledge_snapshot_id: Text
    knowledge_snapshot_digest: Digest
    ontology_digest: Digest
    selection_policy: Literal["first-effective-accepted-per-cve-v1"] = (
        "first-effective-accepted-per-cve-v1"
    )
    source_digests: dict[str, Digest]
    recommendation: CVERecommendation
    action_execution: Literal["not_performed"] = "not_performed"

    @model_validator(mode="after")
    def correlate(self):
        if (
            set(self.source_digests) != set(SOURCES)
            or self.recommendation.ranking_decision_id != self.ranking_decision_id
        ):
            raise ValueError("Finalization source set or parent ranking differs")
        for row in self.recommendation.candidates:
            context = row.validation.request.operational_context
            if (
                context.run_id != self.run_id
                or context.asset_id != self.asset_id
                or context.evidence_digest != self.source_digests["runtime_evidence"]
                or context.candidates_digest != self.source_digests["candidate_strategies"]
            ):
                raise ValueError("Finalization differs from validated run/asset/source digests")
        return self

    @property
    def finalization_id(self):
        parts = [
            self.tenant_id,
            self.run_id,
            self.asset_id,
            self.recommendation.cve_id,
            self.ranking_decision_id,
        ]
        raw = "".join(f"{len(value.encode('utf-8'))}:{value}" for value in parts)
        return "FIN_" + hashlib.sha256(raw.encode("utf-8")).hexdigest()


class RecommendationProvenance(SharedProvenance):
    finalization_id: FinalizationID = Field(alias="finalizationId")


class StoredFinalization(WireModel):
    contract: Literal["shared-finalization-record-v1"]
    finalization_id: FinalizationID
    tenant_id: Text
    document_json: str
    document_sha256: Digest
    provenance_json: str
    provenance_sha256: Digest
    transaction_id: Text

    @property
    def document(self):
        return FinalizationDocument.model_validate(strict_json(self.document_json))

    @property
    def provenance(self):
        return RecommendationProvenance.model_validate(strict_json(self.provenance_json))

    @model_validator(mode="after")
    def integrity(self):
        doc, prov = self.document, self.provenance
        if (
            self.document_sha256 != raw_digest(self.document_json)
            or self.provenance_sha256 != raw_digest(self.provenance_json)
            or self.finalization_id != doc.finalization_id
            or self.tenant_id != doc.tenant_id
            or prov.finalization_id != self.finalization_id
            or prov.decision_id != doc.ranking_decision_id
            or prov.knowledge_snapshot_id != doc.knowledge_snapshot_id
            or prov.knowledge_snapshot_digest != doc.knowledge_snapshot_digest
            or prov.slsa_assurance.ontology_digest != doc.ontology_digest
        ):
            raise ValueError("Ledger record/document/provenance identity or digest differs")
        entities = {row["id"]: row for row in prov.entities}
        activities = {row["id"]: row for row in prov.activities}
        agents = {row["id"]: row for row in prov.agents}
        if any(
            len(rows) != len(index)
            for rows, index in (
                (prov.entities, entities),
                (prov.activities, activities),
                (prov.agents, agents),
            )
        ):
            raise ValueError("Duplicate PROV identity")
        all_ids = set(entities) | set(activities) | set(agents)
        if len(all_ids) != len(entities) + len(activities) + len(agents):
            raise ValueError("PROV identity used for incompatible kinds")
        for relation in prov.relations:
            if relation.get("subject") not in all_ids or relation.get("object") not in all_ids:
                raise ValueError("Dangling PROV reference")
        for activity in prov.activities:
            if not set(activity.get("usedEntities", [])) <= set(entities):
                raise ValueError("Unknown PROV input entity")
        relations = {(r["subject"], r["predicate"], r["object"]) for r in prov.relations}
        final_uri = f"urn:cti:recommendation:{self.finalization_id}"
        attrs = entities.get(final_uri, {}).get("attributes", {})
        expected = {
            "document_sha256": self.document_sha256,
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
        }
        if any(key not in attrs or attrs[key] != value for key, value in expected.items()):
            raise ValueError("Provenance describes another recommendation")
        for name, sha in doc.source_digests.items():
            matching = [
                e
                for e in prov.entities
                if e.get("attributes", {}).get("artifact_name") == name
                and e["attributes"].get("sha256") == sha
            ]
            if len(matching) != 1:
                raise ValueError("Provenance must bind every original producer artifact")
        generators = {o for s, p, o in relations if s == final_uri and p == "prov:wasGeneratedBy"}
        if len(generators) != 1 or not generators <= set(activities):
            raise ValueError("Final recommendation is disconnected from its generation activity")
        generator = next(iter(generators))
        for candidate in doc.recommendation.candidates:
            attempt = candidate.validation
            matching = [
                e
                for e in prov.entities
                if e.get("attributes", {}).get("origin") == "backend_recorded_validation"
                and e["attributes"].get("strategy_id") == attempt.strategy_id
            ]
            if len(matching) != 1:
                raise ValueError("Missing backend validation in provenance")
            entity = matching[0]
            expected_validation = {
                "ontology_individual": attempt.ontology_individual,
                "countermeasure_iri": attempt.request.countermeasure_iri,
                "semantic_status": attempt.response.status,
                "operational_status": attempt.response.operational.status,
                "effective_status": attempt.response.effective_status,
                "context_digest": attempt.response.operational.context_digest,
            }
            if (
                any(entity["attributes"].get(k) != v for k, v in expected_validation.items())
                or (generator, "prov:used", entity["id"]) not in relations
            ):
                raise ValueError("Validation lineage differs or is disconnected")
        return self


class CommitReceipt(WireModel):
    transaction_id: Text
    block_number: Annotated[str, Field(pattern=r"^(0|[1-9][0-9]*)$")]
    validation_code: Literal[0]
    successful: Literal[True]

    @model_validator(mode="before")
    @classmethod
    def exact_types(cls, value):
        if isinstance(value, dict) and (
            type(value.get("validation_code")) is not int
            or type(value.get("successful")) is not bool
        ):
            raise ValueError("Explicit Fabric validation code/success required")
        return value


class FinalizationResponse(WireModel):
    contract: Literal["shared-finalization-response-v1"]
    record: StoredFinalization
    commit: CommitReceipt
    ledger_readback_verified: Literal[True]
    verification_scope: Literal["backend_reported_commit_and_readback"]
    deployment_verified: Literal[False]
    action_execution: Literal["not_performed"]

    @model_validator(mode="before")
    @classmethod
    def explicit_flags(cls, value):
        if isinstance(value, dict) and (
            type(value.get("ledger_readback_verified")) is not bool
            or type(value.get("deployment_verified")) is not bool
        ):
            raise ValueError("Explicit backend verification flags required")
        return value

    @model_validator(mode="after")
    def correlate(self):
        if self.record.transaction_id != self.commit.transaction_id:
            raise ValueError("Receipt differs from stored ledger transaction")
        return self


def finalization_contracts():
    return json.loads(
        files("thesis_agents").joinpath("data/shared-finalization-schemas-v1.json").read_text()
    )
