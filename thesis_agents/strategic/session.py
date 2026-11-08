"""Raccordo canonico -> Strategic -> MCP, senza ricostruire ranking o reasoner."""

import copy
import json
from pathlib import Path
from threading import RLock

from thesis_agents.agents.contracts import ARTIFACT_OWNERS
from thesis_agents.canonical.contracts import PreparationArtifact
from thesis_agents.canonical.preparation import bytes_digest
from thesis_agents.canonical.session import load_prepared_checkpoint
from thesis_agents.strategic.contracts import (
    NativeCVERanking,
    NativeRankingSettings,
    NativeStrategicRanking,
)


class NativeStrategicSession:
    def __init__(self, prepared_dir, output_dir, settings, client):
        self.prepared_dir = Path(prepared_dir)
        self.output_dir = Path(output_dir)
        self.preparation, self.inputs = load_prepared_checkpoint(self.prepared_dir)
        self._input_snapshot = copy.deepcopy(self.inputs)
        self.settings = NativeRankingSettings.model_validate(settings.model_dump())
        self.client = client
        self.backend_kind = client.profile.connection.expected_kind
        if self.preparation.knowledge_snapshot_id != self.settings.knowledge_snapshot_id:
            raise ValueError("Strategic snapshot differs from canonical preparation")
        names = [
            "canonical_preparation.json",
            "request.json",
            "profile.json",
            "aln_ontology.owl",
            "observed_assets.owl",
            *(f"inputs/{name}.json" for name in self.inputs),
            *(f"ranking-requests/{g.cve_id}.json" for g in self.preparation.graphs),
        ]
        self._source_bytes = {name: (self.prepared_dir / name).read_bytes() for name in names}
        # Revalidate the captured bytes before creating any output or contacting MCP.
        checked, inputs = load_prepared_checkpoint(self.prepared_dir)
        if checked != self.preparation or inputs != self.inputs:
            raise ValueError("Preparation changed during loading")
        self._rankings = {}
        self._decisions = {}
        self._provenance = {}
        self._artifact = None
        self._failed = False
        self._operation_lock = RLock()
        self.output_dir.mkdir(parents=True, exist_ok=False)
        for name, raw in self._source_bytes.items():
            target = self.output_dir / "preparation" / name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(raw)
        self._config_bytes = {
            "ranking-profile.json": self.settings.model_dump_json(indent=2).encode(),
            "mcp-profile.json": client.profile.model_dump_json(indent=2).encode(),
        }
        for name, raw in self._config_bytes.items():
            (self.output_dir / name).write_bytes(raw)

    def _check_sources(self):
        for name, raw in self._source_bytes.items():
            for root in (self.prepared_dir, self.output_dir / "preparation"):
                if (root / name).read_bytes() != raw:
                    raise ValueError("Canonical Strategic input changed")
        for name, raw in self._config_bytes.items():
            if (self.output_dir / name).read_bytes() != raw:
                raise ValueError("Strategic profile changed")
        if (
            NativeRankingSettings.model_validate_json(self._config_bytes["ranking-profile.json"])
            != self.settings
        ):
            raise ValueError("Strategic configuration changed")
        if self.preparation != PreparationArtifact.model_validate_json(
            self._source_bytes["canonical_preparation.json"]
        ):
            raise ValueError("In-memory canonical preparation changed")
        if self.inputs != self._input_snapshot:
            raise ValueError("In-memory MAS input changed")
        if json.loads(self.client.profile.model_dump_json(indent=2)) != json.loads(
            self._config_bytes["mcp-profile.json"]
        ):
            raise ValueError("MCP profile changed")

    def get_context(self) -> dict:
        """Read MAS producers and the canonical checkpoint, retaining their separate identities.

        Returns:
            dict: Authoritative artifacts, explicit bindings and pending operation.
        """
        self._check_sources()
        return {
            "run_id": self.preparation.run_id,
            "asset_id": self.preparation.asset_id,
            "artifacts": {
                **copy.deepcopy(self.inputs),
                "canonical_preparation": self.preparation.model_dump(mode="json", by_alias=True),
            },
            "artifact_producers": {
                **{name: ARTIFACT_OWNERS[name] for name in self.inputs},
                "canonical_preparation": "SemanticPreparationAgent",
            },
            "next_operation": self.next_operation(),
            "semantic_validation": "pending",
            "recommendation": "pending",
        }

    def next_operation(self):
        if self._failed or self._artifact is not None:
            return None
        for cve in sorted(g.cve_id for g in self.preparation.graphs):
            for mapping, name in (
                (self._rankings, "rank_remediations"),
                (self._decisions, "get_decision"),
                (self._provenance, "get_provenance"),
            ):
                if cve not in mapping:
                    return {"tool": name, "cve_id": cve}
        return {"tool": "publish_native_ranking"}

    def _execute(self, tool, cve_id, mapping):
        # A model can issue duplicate calls in a batch; only one may mutate SaaS.
        with self._operation_lock:
            return self._execute_locked(tool, cve_id, mapping)

    def _execute_locked(self, tool, cve_id, mapping):
        self._check_sources()
        self._check_responses()
        if self.next_operation() != {"tool": tool, "cve_id": cve_id}:
            raise ValueError("Strategic tool/CVE out of phase; no remote call made")
        graph = next(g for g in self.preparation.graphs if g.cve_id == cve_id)
        event = {"tool": tool, "cve_id": cve_id}
        try:
            if tool == "rank_remediations":
                # Only the configured canonical request is sent, never model-supplied scores/IDs.
                response = self.client.rank_remediations(
                    graph.ranking_request.model_copy(deep=True)
                )
            else:
                response = getattr(self.client, tool)(self._rankings[cve_id].decision_id)
            # Retain even responses rejected by the stricter Strategic deployment pins.
            target = self.output_dir / "native" / cve_id / f"{tool}.json"
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("x") as stream:
                stream.write(response.model_dump_json(indent=2, by_alias=True) + "\n")
            self._check_sources()
            if tool == "rank_remediations":
                if (
                    response.tenant_id != self.settings.tenant_id
                    or response.knowledge_snapshot_id != self.settings.knowledge_snapshot_id
                    or response.knowledge_snapshot_digest != self.settings.knowledge_snapshot_digest
                    or response.slsa_assurance.ontology_digest != self.settings.ontology_digest
                    or any(r.decision_id == response.decision_id for r in self._rankings.values())
                ):
                    raise ValueError("Native ranking differs from tenant/snapshot/ontology pins")
            mapping[cve_id] = response.model_copy(deep=True)
            event["status"] = "validated"
            return response.model_dump(mode="json", by_alias=True)
        except BaseException as exc:
            self._failed = True  # No automatic retry after an uncertain backend mutation.
            event.update(status="failed", error_type=type(exc).__name__)
            raise
        finally:
            with (self.output_dir / "strategic_events.jsonl").open("a") as stream:
                stream.write(json.dumps(event) + "\n")

    def rank_remediations(self, cve_id: str) -> dict:
        """Send the exact canonical graph and candidates for the required CVE to SaaS.

        Args:
            cve_id: The CVE indicated by next_operation; never a list of CVEs.

        Returns:
            dict: Original native ranking with unmodified scores and KG IDs.
        """
        return self._execute("rank_remediations", cve_id, self._rankings)

    def get_decision(self, cve_id: str) -> dict:
        """Read back the SaaS ranking decision associated with the required CVE.

        Args:
            cve_id: CVE of the immediately preceding ranking.

        Returns:
            dict: Validated shared decision record, retaining original assurance.
        """
        return self._execute("get_decision", cve_id, self._decisions)

    def get_provenance(self, cve_id: str) -> dict:
        """Read the provenance of the SaaS ranking record for the required CVE.

        Args:
            cve_id: CVE whose SaaS decision has just been read back.

        Returns:
            dict: Ranking provenance; does not certify a final MAS recommendation.
        """
        return self._execute("get_provenance", cve_id, self._provenance)

    def _build_artifact(self):
        return NativeStrategicRanking(
            run_id=self.preparation.run_id,
            asset_id=self.preparation.asset_id,
            preparation_sha256=bytes_digest(self._source_bytes["canonical_preparation.json"]),
            source_ontology_sha256=self.preparation.source_ontology_sha256,
            aln_ontology_sha256=self.preparation.aln_ontology_sha256,
            settings=self.settings,
            backend_kind=self.backend_kind,
            results=[
                NativeCVERanking(
                    cve_id=cve,
                    bindings=[b for b in self.preparation.bindings if b.cve_id == cve],
                    ranking=self._rankings[cve],
                    decision_readback=self._decisions[cve],
                    provenance_readback=self._provenance[cve],
                )
                for cve in sorted(self._rankings)
            ],
        )

    def _check_responses(self):
        for tool, mapping in (
            ("rank_remediations", self._rankings),
            ("get_decision", self._decisions),
            ("get_provenance", self._provenance),
        ):
            for cve, response in mapping.items():
                path = self.output_dir / "native" / cve / f"{tool}.json"
                stored = json.loads(path.read_bytes())
                if stored != response.model_dump(mode="json", by_alias=True):
                    raise ValueError("Stored native response changed")

    def publish_native_ranking(self) -> dict:
        """Publish the checkpoint only after every CVE ranking and both readbacks succeeded.

        Returns:
            dict: Correlated native rankings and bindings; semantic selection remains pending.
        """
        with self._operation_lock:
            return self._publish()

    def _publish(self):
        if self._artifact is not None:
            return self.assert_complete().model_dump(mode="json", by_alias=True)
        self._check_sources()
        if self.next_operation() != {"tool": "publish_native_ranking"}:
            raise ValueError("Native rankings/readbacks incomplete or failed")
        self._check_responses()
        artifact = self._build_artifact()
        with (self.output_dir / "native_strategic_ranking.json").open("x") as stream:
            stream.write(artifact.model_dump_json(indent=2, by_alias=True) + "\n")
        self._artifact = artifact.model_copy(deep=True)
        return self.assert_complete().model_dump(mode="json", by_alias=True)

    def assert_complete(self):
        self._check_sources()
        self._check_responses()
        if self._failed or self._artifact is None:
            raise ValueError("Native Strategic ranking unpublished or failed")
        stored = NativeStrategicRanking.model_validate_json(
            (self.output_dir / "native_strategic_ranking.json").read_bytes()
        )
        if stored != self._artifact or stored != self._build_artifact():
            raise ValueError("Published native Strategic ranking changed")
        if {r.cve_id for r in stored.results} != {g.cve_id for g in self.preparation.graphs}:
            raise ValueError("Incomplete CVE coverage in native Strategic ranking")
        return stored
