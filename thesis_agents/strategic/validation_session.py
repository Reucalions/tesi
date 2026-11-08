"""Caricamento del ranking e validazioni native in ordine, con profilo operatore fissato."""

import copy
import json
from pathlib import Path
from threading import RLock

from thesis_agents.canonical.preparation import bytes_digest
from thesis_agents.canonical.session import load_prepared_checkpoint
from thesis_agents.mcp.client import digest
from thesis_agents.mcp.operational_contracts import ConstraintMapping, OperationalContext
from thesis_agents.mcp.shared_contracts import ValidateCountermeasureRequest
from thesis_agents.strategic.contracts import NativeRankingSettings, NativeStrategicRanking
from thesis_agents.strategic.validation_contracts import (
    NativeStrategicValidation,
    NativeValidationAttempt,
    ValidationProfile,
)


def load_ranking_checkpoint(directory):
    directory = Path(directory)
    ranking = NativeStrategicRanking.model_validate_json(
        (directory / "native_strategic_ranking.json").read_bytes()
    )
    preparation, inputs = load_prepared_checkpoint(directory / "preparation")
    if (
        ranking.run_id != preparation.run_id
        or ranking.asset_id != preparation.asset_id
        or ranking.preparation_sha256
        != bytes_digest((directory / "preparation/canonical_preparation.json").read_bytes())
        or ranking.aln_ontology_sha256 != preparation.aln_ontology_sha256
        or ranking.source_ontology_sha256 != preparation.source_ontology_sha256
        or {r.cve_id for r in ranking.results} != {g.cve_id for g in preparation.graphs}
        or ranking.settings
        != NativeRankingSettings.model_validate_json(
            (directory / "ranking-profile.json").read_bytes()
        )
    ):
        raise ValueError("Ranking checkpoint differs from canonical preparation/profile")
    for result in ranking.results:
        graph = next(g for g in preparation.graphs if g.cve_id == result.cve_id)
        expected = [b for b in preparation.bindings if b.cve_id == result.cve_id]

        def key(binding):
            return binding.cve_id, binding.strategy_id

        if (
            sorted(result.bindings, key=key) != sorted(expected, key=key)
            or result.ranking.slsa_assurance.input_digest
            != "sha256:" + digest(graph.ranking_request.rest_payload())
            or {r.id: r.name for r in result.ranking.ranked_strategies}
            != {c.id: c.name for c in graph.ranking_request.candidates}
        ):
            raise ValueError("Ranking request/digest/bindings differ from canonical preparation")
        for tool, model in (
            ("rank_remediations", result.ranking),
            ("get_decision", result.decision_readback),
            ("get_provenance", result.provenance_readback),
        ):
            path = directory / "native" / result.cve_id / f"{tool}.json"
            if json.loads(path.read_bytes()) != model.model_dump(mode="json", by_alias=True):
                raise ValueError("Native response differs from published ranking checkpoint")
    return ranking, preparation, inputs


def validation_requests(ranking, preparation, inputs, profile):
    """Resolve exact candidate/IRI requests identically for execution and archived verification."""
    expected = {(b.cve_id, b.strategy_id, b.ontology_individual) for b in preparation.bindings}
    actual = {(b.cve_id, b.strategy_id, b.ontology_individual) for b in profile.bindings}
    if actual != expected:
        raise ValueError("Validation IRI bindings must exactly cover canonical MAS/KG pairs")
    requests = {}
    candidates = {c["id"]: c for c in inputs["candidate_strategies"]["strategies"]}
    valid_mappings = {
        (c["id"], constraint) for c in candidates.values() for constraint in c["constraints"]
    }
    if not {(m.strategy_id, m.constraint) for m in profile.constraint_mappings} <= valid_mappings:
        raise ValueError("Constraint mapping differs from MAS candidate constraints")
    for result in ranking.results:
        for row in result.ranking.ranked_strategies:
            binding = next(
                b
                for b in profile.bindings
                if b.cve_id == result.cve_id and b.ontology_individual == row.id
            )
            candidate = candidates[binding.strategy_id]
            context = OperationalContext(
                run_id=profile.run_id,
                asset_id=profile.asset_id,
                cve_id=result.cve_id,
                strategy_id=binding.strategy_id,
                ranking_decision_id=result.ranking.decision_id,
                ontology_individual=row.id,
                action=candidate["action"],
                prerequisites=candidate["prerequisites"],
                constraints=candidate["constraints"],
                available_capabilities=profile.available_capabilities,
                prohibited_actions=profile.prohibited_actions,
                constraint_mappings=[
                    ConstraintMapping(
                        constraint=m.constraint, required_capabilities=m.required_capabilities
                    )
                    for m in profile.constraint_mappings
                    if m.strategy_id == binding.strategy_id
                ],
                evidence_digest="sha256:" + preparation.input_digests["runtime_evidence"],
                candidates_digest="sha256:" + preparation.input_digests["candidate_strategies"],
                policy_source=profile.policy_source,
            )
            requests[(result.cve_id, binding.strategy_id)] = ValidateCountermeasureRequest(
                asset_iri=profile.asset_iri,
                countermeasure_iri=binding.countermeasure_iri,
                ontology_id=profile.ontology_key,
                operational_context=context,
            )
    return requests


class NativeValidationSession:
    def __init__(self, ranking_dir, output_dir, profile, client):
        self.ranking_dir, self.output_dir = Path(ranking_dir), Path(output_dir)
        self.ranking, self.preparation, self.inputs = load_ranking_checkpoint(self.ranking_dir)
        self.profile = ValidationProfile.model_validate(profile.model_dump())
        self.client = client
        ranking_raw = (self.ranking_dir / "native_strategic_ranking.json").read_bytes()
        if (
            self.profile.ranking_sha256 != bytes_digest(ranking_raw)
            or self.profile.run_id != self.ranking.run_id
            or self.profile.asset_id != self.ranking.asset_id
            or client.profile.connection.expected_kind != self.ranking.backend_kind
        ):
            raise ValueError("Validation profile/run/backend differs from ranking checkpoint")
        self._requests = validation_requests(
            self.ranking, self.preparation, self.inputs, self.profile
        )
        files = ["native_strategic_ranking.json", "ranking-profile.json", "mcp-profile.json"]
        files += [
            str(p.relative_to(self.ranking_dir))
            for folder in ("preparation", "native")
            for p in (self.ranking_dir / folder).rglob("*")
            if p.is_file()
        ]
        self._source_bytes = {name: (self.ranking_dir / name).read_bytes() for name in files}
        # No server is started by the constructor. All bindings are checked first.
        checked = load_ranking_checkpoint(self.ranking_dir)
        if (
            checked != (self.ranking, self.preparation, self.inputs)
            or bytes_digest(self._source_bytes["native_strategic_ranking.json"])
            != self.profile.ranking_sha256
        ):
            raise ValueError("Ranking changed during validation loading")
        self._profile_raw = self.profile.model_dump_json(indent=2).encode()
        self._mcp_raw = client.profile.model_dump_json(indent=2).encode()
        self._request_bytes = {
            key: request.model_dump_json(indent=2).encode()
            for key, request in self._requests.items()
        }
        self._attempts = {}
        self._artifact, self._failed = None, False
        self._lock = RLock()
        self.output_dir.mkdir(parents=True, exist_ok=False)
        for name, raw in self._source_bytes.items():
            path = self.output_dir / "ranking-input" / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
        (self.output_dir / "validation-profile.json").write_bytes(self._profile_raw)
        (self.output_dir / "mcp-profile.json").write_bytes(self._mcp_raw)

    def _check(self):
        for name, raw in self._source_bytes.items():
            if any(
                (root / name).read_bytes() != raw
                for root in (self.ranking_dir, self.output_dir / "ranking-input")
            ):
                raise ValueError("Validation ranking input changed")
        if (
            (self.output_dir / "validation-profile.json").read_bytes() != self._profile_raw
            or self.profile != ValidationProfile.model_validate_json(self._profile_raw)
            or (self.output_dir / "mcp-profile.json").read_bytes() != self._mcp_raw
            or self.client.profile.model_dump_json(indent=2).encode() != self._mcp_raw
        ):
            raise ValueError("Validation profile changed")
        for (cve, strategy), attempt in self._attempts.items():
            path = self.output_dir / "attempts" / cve / f"{strategy}.json"
            if NativeValidationAttempt.model_validate_json(path.read_bytes()) != attempt:
                raise ValueError("Stored validation response changed")
        for (cve, strategy), raw in self._request_bytes.items():
            if self._requests[(cve, strategy)].model_dump_json(indent=2).encode() != raw:
                raise ValueError("Configured validation request changed")
            path = self.output_dir / "attempts" / cve / f"{strategy}.request.json"
            if path.exists() and path.read_bytes() != raw:
                raise ValueError("Stored validation request changed")

    def get_context(self) -> dict:
        """Read the distinct MAS inputs, native ranking and explicit operator policy.

        Returns:
            dict: Source artifacts and the next required CVE/strategy validation.
        """
        self._check()
        return {
            "artifacts": {
                **copy.deepcopy(self.inputs),
                "canonical_preparation": self.preparation.model_dump(mode="json", by_alias=True),
                "native_strategic_ranking": self.ranking.model_dump(mode="json", by_alias=True),
                "operational_profile": self.profile.model_dump(mode="json"),
            },
            "artifact_producers": {
                "runtime_evidence": "TelemetryAgent",
                "vulnerability_report": "VulnerabilityAgent",
                "candidate_strategies": "CountermeasureAgent",
                "canonical_preparation": "SemanticPreparationAgent",
                "native_strategic_ranking": "StrategicAgent",
                "operational_profile": "Operator",
            },
            "next_operation": self.next_operation(),
        }

    def next_operation(self):
        if self._failed or self._artifact is not None:
            return None
        for cve, strategy in self._requests:
            if (cve, strategy) not in self._attempts:
                return {"tool": "validate_countermeasure", "cve_id": cve, "strategy_id": strategy}
        return {"tool": "publish_native_validation"}

    def validate_countermeasure(self, cve_id: str, strategy_id: str) -> dict:
        """Submit the fixed native IRI request with the complete operational context.

        Args:
            cve_id: Required CVE from next_operation.
            strategy_id: Required MAS strategy ID, resolved through exact KG/IRI bindings.

        Returns:
            dict: Tiny-ME result, SaaS policy assessment and effective eligibility status.
        """
        with self._lock:
            self._check()
            if self.next_operation() != {
                "tool": "validate_countermeasure",
                "cve_id": cve_id,
                "strategy_id": strategy_id,
            }:
                raise ValueError("Validation tool/CVE/strategy out of phase")
            request = self._requests[(cve_id, strategy_id)].model_copy(deep=True)
            event = {
                "tool": "validate_countermeasure",
                "cve_id": cve_id,
                "strategy_id": strategy_id,
            }
            path = self.output_dir / "attempts" / cve_id / f"{strategy_id}.json"
            path.parent.mkdir(parents=True, exist_ok=True)
            (path.parent / f"{strategy_id}.request.json").write_text(
                request.model_dump_json(indent=2)
            )
            try:
                response = self.client.validate_countermeasure(request)
                context = request.operational_context
                attempt = NativeValidationAttempt(
                    cve_id=cve_id,
                    strategy_id=strategy_id,
                    ontology_individual=context.ontology_individual,
                    ranking_decision_id=context.ranking_decision_id,
                    request=request,
                    response=response,
                )
                self._check()
                with path.open("x") as stream:
                    stream.write(attempt.model_dump_json(indent=2, by_alias=True) + "\n")
                self._attempts[(cve_id, strategy_id)] = attempt.model_copy(deep=True)
                event["status"] = "validated"
                return attempt.model_dump(mode="json", by_alias=True)
            except BaseException as exc:
                self._failed = True
                event.update(status="failed", error_type=type(exc).__name__)
                raise
            finally:
                with (self.output_dir / "validation_events.jsonl").open("a") as stream:
                    stream.write(json.dumps(event) + "\n")

    def _build(self):
        return NativeStrategicValidation(
            run_id=self.profile.run_id,
            asset_id=self.profile.asset_id,
            ranking_sha256=self.profile.ranking_sha256,
            profile_sha256=bytes_digest(self._profile_raw),
            attempts=list(self._attempts.values()),
        )

    def publish_native_validation(self) -> dict:
        """Publish all ordered validations; recommendation and shared finalization remain pending.

        Returns:
            dict: Complete validation checkpoint, preserving semantic and operational outcomes.
        """
        with self._lock:
            self._check()
            if self._artifact is not None:
                return self.assert_complete().model_dump(mode="json", by_alias=True)
            if self.next_operation() != {"tool": "publish_native_validation"}:
                raise ValueError("Native validations incomplete or failed")
            artifact = self._build()
            with (self.output_dir / "native_strategic_validation.json").open("x") as stream:
                stream.write(artifact.model_dump_json(indent=2, by_alias=True) + "\n")
            self._artifact = artifact.model_copy(deep=True)
            return self.assert_complete().model_dump(mode="json", by_alias=True)

    def assert_complete(self):
        self._check()
        if self._failed or self._artifact is None:
            raise ValueError("Native validation unpublished or failed")
        stored = NativeStrategicValidation.model_validate_json(
            (self.output_dir / "native_strategic_validation.json").read_bytes()
        )
        if (
            stored != self._artifact
            or stored != self._build()
            or list(self._attempts) != list(self._requests)
        ):
            raise ValueError("Published native validations changed or incomplete")
        return stored
