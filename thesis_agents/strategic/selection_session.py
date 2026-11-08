"""Verified archived validation -> immutable native recommendation; no backend calls."""

import copy
import json
from pathlib import Path
from threading import RLock

from thesis_agents.canonical.preparation import bytes_digest
from thesis_agents.mcp.shared_client import SharedMCPProfile
from thesis_agents.strategic.selection_contracts import (
    CandidateAssessment,
    CVERecommendation,
    NativeStrategicRecommendation,
    selection_outcome,
)
from thesis_agents.strategic.validation_contracts import (
    NativeStrategicValidation,
    NativeValidationAttempt,
    ValidationProfile,
)
from thesis_agents.strategic.validation_session import load_ranking_checkpoint, validation_requests


def load_validation_checkpoint(directory):
    """Require complete, correlated requests/responses in the exact native ranking order."""
    directory = Path(directory)
    validation = NativeStrategicValidation.model_validate_json(
        (directory / "native_strategic_validation.json").read_bytes()
    )
    profile_raw = (directory / "validation-profile.json").read_bytes()
    profile = ValidationProfile.model_validate_json(profile_raw)
    ranking, preparation, inputs = load_ranking_checkpoint(directory / "ranking-input")
    connection = SharedMCPProfile.load(directory / "mcp-profile.json").connection
    ranking_connection = SharedMCPProfile.load(
        directory / "ranking-input/mcp-profile.json"
    ).connection
    if (
        validation.run_id != profile.run_id
        or validation.asset_id != profile.asset_id
        or profile.run_id != ranking.run_id
        or profile.asset_id != ranking.asset_id
        or validation.ranking_sha256 != profile.ranking_sha256
        or profile.ranking_sha256
        != bytes_digest((directory / "ranking-input/native_strategic_ranking.json").read_bytes())
        or validation.profile_sha256 != bytes_digest(profile_raw)
        or connection.expected_kind != ranking.backend_kind
        or ranking_connection.expected_kind != ranking.backend_kind
    ):
        raise ValueError("Validation checkpoint differs from ranking/profile/backend")
    requests = validation_requests(ranking, preparation, inputs, profile)
    if [(a.cve_id, a.strategy_id) for a in validation.attempts] != list(requests):
        raise ValueError("Validation attempts incomplete, duplicated or outside native order")
    for attempt in validation.attempts:
        request = requests[(attempt.cve_id, attempt.strategy_id)]
        path = directory / "attempts" / attempt.cve_id / f"{attempt.strategy_id}.json"
        if (
            attempt.request != request
            or NativeValidationAttempt.model_validate_json(path.read_bytes()) != attempt
            or json.loads(path.with_suffix(".request.json").read_bytes())
            != request.model_dump(mode="json")
        ):
            raise ValueError("Stored validation differs from fixed request/attempt checkpoint")
    return validation, profile, ranking, preparation, inputs


def recommendation_from_checkpoint(checkpoint, validation_sha256):
    validation, profile, ranking, _, _ = checkpoint
    results = []
    for result in ranking.results:
        attempts = [a for a in validation.attempts if a.cve_id == result.cve_id]
        selected = next((a for a in attempts if a.response.effective_status == "accepted"), None)
        results.append(
            CVERecommendation(
                cve_id=result.cve_id,
                ranking_decision_id=result.ranking.decision_id,
                outcome=selection_outcome(attempts),
                selected_strategy_id=selected.strategy_id if selected else None,
                candidates=[
                    CandidateAssessment(
                        ranking=row,
                        validation=attempt,
                        disposition=(
                            "selected"
                            if attempt is selected
                            else "lower_ranked_acceptable"
                            if attempt.response.effective_status == "accepted"
                            else "not_acceptable"
                        ),
                    )
                    for row, attempt in zip(result.ranking.ranked_strategies, attempts, strict=True)
                ],
            )
        )
    return NativeStrategicRecommendation(
        run_id=validation.run_id,
        asset_id=validation.asset_id,
        ranking_sha256=validation.ranking_sha256,
        validation_sha256=validation_sha256,
        validation_profile_sha256=validation.profile_sha256,
        backend_kind=ranking.backend_kind,
        results=results,
    )


class NativeSelectionSession:
    def __init__(self, validation_dir, output_dir):
        self.validation_dir, self.output_dir = Path(validation_dir), Path(output_dir)
        self._checkpoint = load_validation_checkpoint(self.validation_dir)
        self._source_bytes = {
            str(p.relative_to(self.validation_dir)): p.read_bytes()
            for p in self.validation_dir.rglob("*")
            if p.is_file()
        }
        self._expected = recommendation_from_checkpoint(
            self._checkpoint, bytes_digest(self._source_bytes["native_strategic_validation.json"])
        )
        if load_validation_checkpoint(self.validation_dir) != self._checkpoint:
            raise ValueError("Validation changed during selection loading")
        self._artifact, self._failed = None, False
        self._lock = RLock()
        self.output_dir.mkdir(parents=True, exist_ok=False)
        for name, raw in self._source_bytes.items():
            path = self.output_dir / "validation-input" / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)
        self._check()

    def _check(self):
        for name, raw in self._source_bytes.items():
            if any(
                (root / name).read_bytes() != raw
                for root in (self.validation_dir, self.output_dir / "validation-input")
            ):
                raise ValueError("Selection validation input changed")
        checked = load_validation_checkpoint(self.output_dir / "validation-input")
        if checked != self._checkpoint or self._expected != recommendation_from_checkpoint(
            checked,
            bytes_digest(self._source_bytes["native_strategic_validation.json"]),
        ):
            raise ValueError("Selection checkpoint changed")

    def get_context(self) -> dict:
        """Read original producer artifacts, native scores and all fixed validation outcomes.

        Returns:
            dict: Verified lineage and the required recommendation publication operation.
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
                    "operational_profile": profile.model_dump(mode="json"),
                },
                "artifact_producers": {
                    "runtime_evidence": "TelemetryAgent",
                    "vulnerability_report": "VulnerabilityAgent",
                    "candidate_strategies": "CountermeasureAgent",
                    "canonical_preparation": "SemanticPreparationAgent",
                    "native_strategic_ranking": "StrategicAgent",
                    "native_strategic_validation": "StrategicAgent",
                    "operational_profile": "Operator",
                },
                "selection_policy": self._expected.selection_policy,
                "next_operation": self.next_operation(),
            }

    def next_operation(self):
        return (
            None
            if self._failed or self._artifact is not None
            else {"tool": "publish_native_recommendation"}
        )

    def publish_native_recommendation(self) -> dict:
        """Publish the first acceptable candidate per CVE, or the verified abstention reason.

        Returns:
            dict: Native scores, every assessment and the dry-run recommendation with lineage.
        """
        with self._lock:
            try:
                self._check()
                if self._failed:
                    raise ValueError("Selection has failed")
                if self._artifact is None:
                    with (self.output_dir / "native_strategic_recommendation.json").open("x") as f:
                        f.write(self._expected.model_dump_json(indent=2, by_alias=True) + "\n")
                    self._artifact = self._expected.model_copy(deep=True)
                return self.assert_complete().model_dump(mode="json", by_alias=True)
            except BaseException:
                self._failed = True
                raise

    def assert_complete(self):
        self._check()
        if self._failed or self._artifact is None:
            raise ValueError("Native recommendation unpublished or failed")
        stored = NativeStrategicRecommendation.model_validate_json(
            (self.output_dir / "native_strategic_recommendation.json").read_bytes()
        )
        if stored != self._artifact or stored != self._expected:
            raise ValueError("Published recommendation differs from validation/ranking")
        return stored
