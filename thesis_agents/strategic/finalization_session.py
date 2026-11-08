"""Verified selection -> immutable shared registration -> independent tool readback."""

import copy
from pathlib import Path
from threading import RLock
from typing import Literal

from pydantic import Field, model_validator

from thesis_agents.canonical.preparation import bytes_digest
from thesis_agents.mcp.finalization_contracts import FinalizationDocument, FinalizationResponse
from thesis_agents.mcp.shared_contracts import WireModel
from thesis_agents.schemas.base import Identifier, require_unique
from thesis_agents.strategic.selection_contracts import NativeStrategicRecommendation
from thesis_agents.strategic.selection_session import (
    load_validation_checkpoint,
    recommendation_from_checkpoint,
)


def load_selection_checkpoint(directory):
    directory = Path(directory)
    checkpoint = load_validation_checkpoint(directory / "validation-input")
    recommendation = NativeStrategicRecommendation.model_validate_json(
        (directory / "native_strategic_recommendation.json").read_bytes()
    )
    if recommendation != recommendation_from_checkpoint(
        checkpoint,
        bytes_digest(
            (directory / "validation-input/native_strategic_validation.json").read_bytes()
        ),
    ):
        raise ValueError("Selection checkpoint differs from original ranking and validations")
    return recommendation, checkpoint


class NativeStrategicFinalization(WireModel):
    contract: Literal["native-strategic-finalization-v1"] = "native-strategic-finalization-v1"
    run_id: Identifier
    asset_id: Identifier
    backend_kind: Literal["mock", "real"]
    results: list[FinalizationResponse] = Field(min_length=1)
    status: Literal["dry_run_completed"] = "dry_run_completed"
    shared_finalization: Literal["completed"] = "completed"
    verification_scope: Literal["backend_reported_commit_and_readback"] = (
        "backend_reported_commit_and_readback"
    )
    deployment_verified: Literal[False] = False
    action_execution: Literal["not_performed"] = "not_performed"

    @model_validator(mode="after")
    def correlate(self):
        require_unique(
            [r.record.document.recommendation.cve_id for r in self.results], "finalized CVEs"
        )
        for response in self.results:
            document = response.record.document
            if document.run_id != self.run_id or document.asset_id != self.asset_id:
                raise ValueError("Finalization belongs to another run/asset")
        return self


class NativeFinalizationSession:
    def __init__(self, selection_dir, output_dir, client):
        self.selection_dir, self.output_dir = Path(selection_dir), Path(output_dir)
        self.recommendation, self._checkpoint = load_selection_checkpoint(self.selection_dir)
        self.client = client
        if (
            not client.finalization_enabled
            or client.profile.connection.expected_kind != self.recommendation.backend_kind
        ):
            raise ValueError(
                "Finalization requires authorized shared tools and matching backend kind"
            )
        self._source_bytes = {
            str(p.relative_to(self.selection_dir)): p.read_bytes()
            for p in self.selection_dir.rglob("*")
            if p.is_file()
        }
        self._documents = self._build_documents()
        self._finalized, self._readbacks = {}, {}
        self._artifact, self._failed, self._lock = None, False, RLock()
        self.output_dir.mkdir(parents=True, exist_ok=False)
        for name, raw in self._source_bytes.items():
            path = self.output_dir / "selection-input" / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
        (self.output_dir / "mcp-profile.json").write_text(
            client.profile.model_dump_json(indent=2) + "\n"
        )
        self._check()

    def _build_documents(self):
        _, _, ranking, preparation, _ = self._checkpoint
        root = "validation-input/"
        ranking_path = root + "ranking-input/"
        prep_path = ranking_path + "preparation/"
        paths = {
            "runtime_evidence": prep_path + "inputs/runtime_evidence.json",
            "vulnerability_report": prep_path + "inputs/vulnerability_report.json",
            "candidate_strategies": prep_path + "inputs/candidate_strategies.json",
            "canonical_preparation": prep_path + "canonical_preparation.json",
            "native_strategic_ranking": ranking_path + "native_strategic_ranking.json",
            "native_strategic_validation": root + "native_strategic_validation.json",
            "validation_profile": root + "validation-profile.json",
            "native_strategic_recommendation": "native_strategic_recommendation.json",
        }
        digests = {
            name: "sha256:" + bytes_digest(self._source_bytes[path]) for name, path in paths.items()
        }
        documents = {}
        for result in self.recommendation.results:
            native = next(r.ranking for r in ranking.results if r.cve_id == result.cve_id)
            key = native.annotated_graph_key
            suffix = "_annotated_graph"
            if not key or not key.endswith(suffix) or not key[: -len(suffix)]:
                raise ValueError(
                    "Original ranking lacks its actual graph key; finalization is unavailable"
                )
            doc = FinalizationDocument(
                run_id=self.recommendation.run_id,
                asset_id=self.recommendation.asset_id,
                tenant_id=ranking.settings.tenant_id,
                ranking_decision_id=native.decision_id,
                ranking_graph_key=key[: -len(suffix)],
                knowledge_snapshot_id=ranking.settings.knowledge_snapshot_id,
                knowledge_snapshot_digest=ranking.settings.knowledge_snapshot_digest,
                ontology_digest=ranking.settings.ontology_digest,
                selection_policy=self.recommendation.selection_policy,
                source_digests=digests,
                recommendation=result,
            )
            documents[result.cve_id] = doc.model_dump_json(by_alias=True)
        return documents

    def _check(self):
        for name, raw in self._source_bytes.items():
            if any(
                (root / name).read_bytes() != raw
                for root in (self.selection_dir, self.output_dir / "selection-input")
            ):
                raise ValueError("Finalization source changed")
        if load_selection_checkpoint(self.output_dir / "selection-input") != (
            self.recommendation,
            self._checkpoint,
        ):
            raise ValueError("Finalization selection/checkpoint changed")
        if self._build_documents() != self._documents:
            raise ValueError("Fixed finalization request changed")
        for cve, response in self._finalized.items():
            if (self.output_dir / "native" / cve / "document.json").read_text() != self._documents[
                cve
            ]:
                raise ValueError("Stored finalization request changed")
            for tool, collection in (
                ("finalize_recommendation", self._finalized),
                ("get_finalization", self._readbacks),
            ):
                if (
                    cve in collection
                    and FinalizationResponse.model_validate_json(
                        (self.output_dir / "native" / cve / f"{tool}.json").read_bytes()
                    )
                    != collection[cve]
                ):
                    raise ValueError("Stored finalization response changed")
            if response.record.document_json != self._documents[cve]:
                raise ValueError("Backend finalized a different document")

    def next_operation(self):
        if self._failed or self._artifact is not None:
            return None
        for cve in self._documents:
            if cve not in self._finalized:
                return {"tool": "finalize_recommendation"}
            if cve not in self._readbacks:
                return {"tool": "read_finalization"}
        return {"tool": "publish_native_finalization"}

    def get_context(self) -> dict:
        """Read verified producer artifacts, fixed selection and finalization progress.

        Returns:
            dict: Original source artifacts and the next required shared operation.
        """
        with self._lock:
            self._check()
            validation, profile, ranking, preparation, inputs = self._checkpoint
            return {
                "artifacts": {
                    **copy.deepcopy(inputs),
                    "canonical_preparation": preparation.model_dump(mode="json", by_alias=True),
                    "native_strategic_ranking": ranking.model_dump(mode="json", by_alias=True),
                    "native_strategic_validation": validation.model_dump(
                        mode="json", by_alias=True
                    ),
                    "validation_profile": profile.model_dump(mode="json"),
                    "native_strategic_recommendation": self.recommendation.model_dump(
                        mode="json", by_alias=True
                    ),
                },
                "next_operation": self.next_operation(),
                "deployment_verified": False,
                "action_execution": "not_performed",
            }

    def _operation(self, tool):
        self._check()
        if self.next_operation() != {"tool": tool}:
            raise ValueError("Finalization operation outside the fixed sequence")

    def finalize_recommendation(self) -> dict:
        """Register the next fixed CVE recommendation through the shared backend.

        Returns:
            dict: Verified backend commit receipt and ledger record; no action execution.
        """
        with self._lock:
            try:
                self._operation("finalize_recommendation")
                cve = next(c for c in self._documents if c not in self._finalized)
                target = self.output_dir / "native" / cve
                target.mkdir(parents=True, exist_ok=False)
                (target / "document.json").write_text(self._documents[cve])
                response = self.client.finalize_recommendation(self._documents[cve])
                ranking = next(r.ranking for r in self._checkpoint[2].results if r.cve_id == cve)
                if response.record.provenance.slsa_assurance != ranking.slsa_assurance:
                    raise ValueError(
                        "Finalization assurance differs from original ranking checkpoint"
                    )
                (target / "finalize_recommendation.json").write_text(
                    response.model_dump_json(indent=2, by_alias=True) + "\n"
                )
                self._finalized[cve] = response.model_copy(deep=True)
                return response.model_dump(mode="json", by_alias=True)
            except BaseException:
                self._failed = True
                raise

    def read_finalization(self) -> dict:
        """Read the registered document, provenance and original commit through MCP.

        Returns:
            dict: Readback matching the original fixed document and commit receipt.
        """
        with self._lock:
            try:
                self._operation("read_finalization")
                cve = next(c for c in self._documents if c not in self._readbacks)
                original = self._finalized[cve]
                response = self.client.get_finalization(
                    original.record.document.ranking_decision_id, original.record.finalization_id
                )
                if response != original:
                    raise ValueError(
                        "Independent finalization readback differs from original receipt/record"
                    )
                (self.output_dir / "native" / cve / "get_finalization.json").write_text(
                    response.model_dump_json(indent=2, by_alias=True) + "\n"
                )
                self._readbacks[cve] = response.model_copy(deep=True)
                return response.model_dump(mode="json", by_alias=True)
            except BaseException:
                self._failed = True
                raise

    def publish_native_finalization(self) -> dict:
        """Publish only after every CVE has a matching receipt, provenance and readback.

        Returns:
            dict: Shared finalization checkpoint with explicit verification scope.
        """
        with self._lock:
            try:
                self._operation("publish_native_finalization")
                result = NativeStrategicFinalization(
                    run_id=self.recommendation.run_id,
                    asset_id=self.recommendation.asset_id,
                    backend_kind=self.recommendation.backend_kind,
                    results=[self._readbacks[cve] for cve in self._documents],
                )
                with (self.output_dir / "native_strategic_finalization.json").open("x") as stream:
                    stream.write(result.model_dump_json(indent=2, by_alias=True) + "\n")
                self._artifact = result.model_copy(deep=True)
                return self.assert_complete().model_dump(mode="json", by_alias=True)
            except BaseException:
                self._failed = True
                raise

    def assert_complete(self):
        self._check()
        if self._failed or self._artifact is None or set(self._readbacks) != set(self._documents):
            raise ValueError("Shared finalization incomplete or failed")
        stored = NativeStrategicFinalization.model_validate_json(
            (self.output_dir / "native_strategic_finalization.json").read_bytes()
        )
        if stored != self._artifact or stored.results != [
            self._readbacks[c] for c in self._documents
        ]:
            raise ValueError("Published finalization changed")
        return stored
