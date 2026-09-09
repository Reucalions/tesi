import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import TypeVar
from uuid import uuid4

from pydantic import BaseModel

from thesis_agents.schemas import (
    ArgumentationGraph,
    CandidateStrategies,
    DecisionContext,
    FinalDecision,
    ProvenanceRecord,
    RankingResult,
    RuntimeEvidence,
    SemanticValidationReport,
    StaticTelemetry,
    VulnerabilityReport,
)
from thesis_agents.schemas.provenance import ProvenanceActivity, ProvenanceEntity
from thesis_agents.tools.interfaces import (
    ProvenanceTool,
    RankingTool,
    SemanticTool,
    VulnerabilityTool,
)
from thesis_agents.tools.provenance_mock import MockProvenanceTool
from thesis_agents.tools.ranking_mock import MockRankingTool, build_graph
from thesis_agents.tools.semantic_mock import MockSemanticTool
from thesis_agents.tools.vulnerability_mock import MockVulnerabilityTool

T = TypeVar("T", bound=BaseModel)
ARTIFACT_SCHEMAS = {
    "runtime_evidence": RuntimeEvidence,
    "vulnerability_report": VulnerabilityReport,
    "candidate_strategies": CandidateStrategies,
    "argumentation_graph": ArgumentationGraph,
    "ranking": RankingResult,
    "semantic_validation": SemanticValidationReport,
    "final_decision": FinalDecision,
    "provenance": ProvenanceRecord,
}

ARTIFACT_PRODUCERS = {
    "runtime_evidence": "TelemetryAgent",
    "vulnerability_report": "VulnerabilityAgent",
    "candidate_strategies": "CountermeasureAgent",
}


class ArtifactSession:
    """Per-run state. Agents publish JSON through validated, stage-specific tools.

    Files are write-once, except the accumulated semantic validation report.
    A retry may repeat the same publication, but cannot rewrite prior evidence.
    """

    def __init__(
        self,
        case: StaticTelemetry,
        output_dir: Path,
        *,
        mode: str = "camel",
        model: str | None = None,
        vulnerability_tool: VulnerabilityTool | None = None,
        ranking_tool: RankingTool | None = None,
        semantic_tool: SemanticTool | None = None,
        provenance_tool: ProvenanceTool | None = None,
    ):
        if mode not in ("camel", "fixtures"):
            raise ValueError("Unknown execution mode")
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        if any(output_dir.iterdir()):
            raise ValueError(f"Output directory must be empty: {output_dir}")
        self.output_dir = output_dir
        self.case = case.model_copy(deep=True)
        self.mode = mode
        self.model = model
        self.run_id = f"run-{uuid4().hex}"
        self.created_at = datetime.now(UTC).isoformat()
        self.vulnerability_tool = vulnerability_tool or MockVulnerabilityTool()
        self.ranking_tool = ranking_tool or MockRankingTool()
        self.semantic_tool = semantic_tool or MockSemanticTool()
        self.provenance_tool = provenance_tool or MockProvenanceTool(output_dir)
        self._artifacts: dict[str, BaseModel] = {}
        self._lookup: VulnerabilityReport | None = None
        self._validation = SemanticValidationReport(validations=[])
        self._commit("input", self.case)

    def _commit(self, name: str, value: T) -> T:
        if name in self._artifacts:
            if self._artifacts[name] != value:
                raise ValueError(f"Artifact {name} is immutable once published")
            return value
        path = self.output_dir / f"{name}.json"
        with path.open("x", encoding="utf-8") as stream:
            stream.write(value.model_dump_json(indent=2) + "\n")
        self._artifacts[name] = value.model_copy(deep=True)
        return value

    def require(self, name: str, schema: type[T]) -> T:
        if name not in self._artifacts:
            raise ValueError(f"Missing prerequisite artifact: {name}")
        return schema.model_validate(self._artifacts[name].model_dump())

    def get_context(self) -> dict:
        """Read authoritative input, validated artifacts, and required JSON schemas.

        Returns:
            dict: Separate artifacts and their producers. StrategicAgent must read
                runtime_evidence, vulnerability_report and candidate_strategies individually.
        """
        return {
            "run_id": self.run_id,
            "mode": self.mode,
            "artifacts": {k: v.model_dump(mode="json") for k, v in self._artifacts.items()},
            "artifact_producers": {
                name: producer if self.mode == "camel" else f"fixture:{producer}"
                for name, producer in ARTIFACT_PRODUCERS.items()
                if name in self._artifacts
            },
            "schemas": {
                k: ARTIFACT_SCHEMAS[k].model_json_schema()
                for k in ("runtime_evidence", "vulnerability_report", "candidate_strategies")
            },
        }

    def _require_strategic_inputs(
        self,
    ) -> tuple[RuntimeEvidence, VulnerabilityReport, CandidateStrategies]:
        """Validate each producer's artifact independently, never a chain summary."""
        return (
            self.require("runtime_evidence", RuntimeEvidence),
            self.require("vulnerability_report", VulnerabilityReport),
            self.require("candidate_strategies", CandidateStrategies),
        )

    def publish_runtime_evidence(self, payload: str) -> dict:
        """Validate and publish the TelemetryAgent's RuntimeEvidence JSON.

        Args:
            payload (str): JSON matching the runtime_evidence schema from get_context.

        Returns:
            dict: Validated RuntimeEvidence; publication fails on altered input facts.
        """
        evidence = RuntimeEvidence.model_validate_json(payload)
        case = self.case
        if (
            evidence.service_name != case.service_name
            or evidence.endpoint_exposed != case.endpoint_exposed
            or evidence.deserialization_observed != case.deserialization_observed
            or len(evidence.software) != 1
            or evidence.software[0].package != case.package_name
            or evidence.software[0].version != case.package_version
        ):
            raise ValueError("RuntimeEvidence must preserve the static telemetry facts")
        return self._commit("runtime_evidence", evidence).model_dump(mode="json")

    def lookup_vulnerabilities(self) -> dict:
        """Query the vulnerability backend for the published software observation.

        Returns:
            dict: Authoritative VulnerabilityReport, ready to publish unchanged.
        """
        evidence = self.require("runtime_evidence", RuntimeEvidence)
        if self._lookup is None:
            result = self.vulnerability_tool.lookup_vulnerabilities(evidence.software[0])
            self._lookup = VulnerabilityReport(
                asset_id=evidence.service_name,
                lookup_status=result.status,
                vulnerabilities=result.vulnerabilities,
            )
        return self._lookup.model_dump(mode="json")

    def publish_vulnerability_report(self, payload: str) -> dict:
        """Validate and publish the backend report without invented CVEs or scores.

        Args:
            payload (str): JSON returned by lookup_vulnerabilities.

        Returns:
            dict: Validated VulnerabilityReport.
        """
        self.require("runtime_evidence", RuntimeEvidence)
        report = VulnerabilityReport.model_validate_json(payload)
        if self._lookup is None or report != self._lookup:
            raise ValueError("Call lookup_vulnerabilities and preserve its exact report")
        return self._commit("vulnerability_report", report).model_dump(mode="json")

    def publish_candidate_strategies(self, payload: str) -> dict:
        """Validate and publish strategies generated by the CountermeasureAgent.

        Args:
            payload (str): JSON matching candidate_strategies from get_context.

        Returns:
            dict: Validated CandidateStrategies with unique IDs and known CVEs.
        """
        self.require("runtime_evidence", RuntimeEvidence)
        report = self.require("vulnerability_report", VulnerabilityReport)
        candidates = CandidateStrategies.model_validate_json(payload)
        known = {v.cve_id for v in report.vulnerabilities}
        if known and not candidates.strategies:
            raise ValueError("Generate at least one strategy for the known vulnerability")
        if not known and candidates.strategies:
            raise ValueError("An unsupported lookup cannot ground remediation strategies")
        for strategy in candidates.strategies:
            if not set(strategy.addressed_vulnerabilities) <= known:
                raise ValueError("Candidate references an unknown vulnerability")
        return self._commit("candidate_strategies", candidates).model_dump(mode="json")

    def build_argumentation_graph(self) -> dict:
        """Project published candidates into strategy, benefit and impact arguments.

        Returns:
            dict: ArgumentationGraph built from the candidates' estimates.
        """
        _, _, candidates = self._require_strategic_inputs()
        graph = build_graph(candidates, f"graph:{self.run_id}")
        return self._commit("argumentation_graph", graph).model_dump(mode="json")

    def rank_graph(self) -> dict:
        """Delegate ranking to the deterministic backend, without LLM scores.

        Returns:
            dict: RankingResult in descending score order; ties use strategy ID.
        """
        graph = self.require("argumentation_graph", ArgumentationGraph)
        if "ranking" in self._artifacts:
            return self.require("ranking", RankingResult).model_dump(mode="json")
        result = RankingResult.model_validate(self.ranking_tool.rank_graph(graph).model_dump())
        ids = {a.strategy_id for a in graph.arguments if a.kind == "strategy"}
        if result.graph_id != graph.id or {r.strategy_id for r in result.ranking} != ids:
            raise ValueError("Ranking backend returned an unrelated graph or candidate set")
        return self._commit("ranking", result).model_dump(mode="json")

    def validate_countermeasure(self, strategy_id: str) -> dict:
        """Validate the next ranked candidate; stop at the first accepted candidate.

        Args:
            strategy_id (str): Next unvalidated strategy ID in the ranking.

        Returns:
            dict: SemanticValidationResult. Rejected candidates require trying the next.
        """
        ranking = self.require("ranking", RankingResult)
        for previous in self._validation.validations:
            if previous.strategy_id == strategy_id:
                return previous.model_dump(mode="json")
        if any(v.valid for v in self._validation.validations):
            raise ValueError("The first accepted candidate has already been found")
        index = len(self._validation.validations)
        if index >= len(ranking.ranking) or ranking.ranking[index].strategy_id != strategy_id:
            raise ValueError("Validate strategies in ranking order without skipping candidates")
        candidates = self.require("candidate_strategies", CandidateStrategies)
        strategy = next(s for s in candidates.strategies if s.id == strategy_id)
        context = DecisionContext(
            evidence=self.require("runtime_evidence", RuntimeEvidence),
            vulnerabilities=self.require("vulnerability_report", VulnerabilityReport),
            available_capabilities=self.case.available_capabilities,
            prohibited_actions=self.case.prohibited_actions,
        )
        result = self.semantic_tool.validate_countermeasure(strategy, context)
        # Revalidate external backend output, including cross-field invariants.
        from thesis_agents.schemas import SemanticValidationResult

        result = SemanticValidationResult.model_validate(result.model_dump())
        if result.strategy_id != strategy_id:
            raise ValueError("Semantic backend returned the wrong strategy ID")
        self._validation.validations.append(result)
        path = self.output_dir / "semantic_validation.json"
        temporary = path.with_suffix(".tmp")
        temporary.write_text(self._validation.model_dump_json(indent=2) + "\n", encoding="utf-8")
        temporary.replace(path)
        self._artifacts["semantic_validation"] = self._validation.model_copy(deep=True)
        return result.model_dump(mode="json")

    def publish_final_decision(self, selected_strategy_id: str | None, explanation: str) -> dict:
        """Publish a decision consistent with the ranking and all validation attempts.

        Args:
            selected_strategy_id (str | None): First accepted strategy, or null if none.
            explanation (str): Explanation grounded in evidence and actual tool results.

        Returns:
            dict: FinalDecision. Scores and validation are copied from backend artifacts.
        """
        ranking = self.require("ranking", RankingResult)
        evidence, report, candidates = self._require_strategic_inputs()
        if {r.strategy_id for r in ranking.ranking} != {s.id for s in candidates.strategies}:
            raise ValueError("Final decision ranking must match the published candidate strategies")
        accepted = next((v for v in self._validation.validations if v.valid), None)
        expected_id = accepted.strategy_id if accepted else None
        if selected_strategy_id != expected_id:
            raise ValueError("Select exactly the first semantically accepted strategy")
        if accepted is None and len(self._validation.validations) != len(ranking.ranking):
            raise ValueError("Validate every ranked strategy before declaring none acceptable")
        if "semantic_validation" not in self._artifacts:
            self._commit("semantic_validation", self._validation)
        status = "selected" if accepted else "no_valid_strategy"
        if report.lookup_status == "unsupported":
            status = "insufficient_evidence"
        decision = FinalDecision(
            status=status,
            selected_strategy_id=expected_id,
            ranking=ranking.ranking,
            semantic_validation=accepted,
            evidence_ids=[s.evidence_id for s in evidence.software],
            explanation=explanation,
        )
        return self._commit("final_decision", decision).model_dump(mode="json")

    def record_provenance(self) -> dict:
        """Record input/output hashes and the agents responsible for each activity.

        Returns:
            dict: Local provenance receipt. Must be called after publishing the decision.
        """
        self.require("final_decision", FinalDecision)
        if "provenance" in self._artifacts:
            return {"run_id": self.run_id, "stored": True}
        stages = [
            ("telemetry", "TelemetryAgent", ["input"], ["runtime_evidence"]),
            ("lookup", "VulnerabilityAgent", ["runtime_evidence"], ["vulnerability_report"]),
            (
                "candidates",
                "CountermeasureAgent",
                ["runtime_evidence", "vulnerability_report"],
                ["candidate_strategies"],
            ),
            ("graph", "StrategicAgent", ["candidate_strategies"], ["argumentation_graph"]),
            ("ranking", "StrategicAgent", ["argumentation_graph"], ["ranking"]),
            (
                "validation",
                "StrategicAgent",
                [
                    "input",
                    "runtime_evidence",
                    "vulnerability_report",
                    "candidate_strategies",
                    "ranking",
                ],
                ["semantic_validation"],
            ),
            (
                "decision",
                "StrategicAgent",
                [
                    "runtime_evidence",
                    "vulnerability_report",
                    "candidate_strategies",
                    "ranking",
                    "semantic_validation",
                ],
                ["final_decision"],
            ),
        ]
        entities = [
            ProvenanceEntity(
                id=name,
                filename=f"{name}.json",
                sha256=hashlib.sha256((self.output_dir / f"{name}.json").read_bytes()).hexdigest(),
            )
            for name in self._artifacts
        ]
        record = ProvenanceRecord(
            run_id=self.run_id,
            mode=self.mode,
            model=self.model,
            created_at=self.created_at,
            entities=entities,
            activities=[
                ProvenanceActivity(
                    id=name,
                    agent=agent if self.mode == "camel" else f"fixture:{agent}",
                    used=used,
                    generated=generated,
                )
                for name, agent, used, generated in stages
            ],
            agents=sorted(
                {agent if self.mode == "camel" else f"fixture:{agent}" for _, agent, _, _ in stages}
            ),
        )
        receipt = self.provenance_tool.record_provenance(record)
        # Keep the local artifact even if a future backend stores provenance remotely.
        path = self.output_dir / "provenance.json"
        if not path.exists():
            self._commit("provenance", record)
        else:
            if ProvenanceRecord.model_validate_json(path.read_text()) != record:
                raise ValueError("Stored provenance differs from the submitted record")
            self._artifacts["provenance"] = record
        return receipt

    def assert_complete(self) -> FinalDecision:
        for name, schema in ARTIFACT_SCHEMAS.items():
            value = self.require(name, schema)
            stored = schema.model_validate_json((self.output_dir / f"{name}.json").read_text())
            if value != stored:
                raise ValueError(f"Stored artifact differs from validated state: {name}")
        return self.require("final_decision", FinalDecision)


def json_payload(value: BaseModel | dict) -> str:
    return value.model_dump_json() if isinstance(value, BaseModel) else json.dumps(value)
