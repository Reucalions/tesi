"""One application entry point; real execution uses native shared contracts without mocks."""

import copy
import json
import os
import subprocess
from contextlib import ExitStack, contextmanager
from hashlib import file_digest
from pathlib import Path

from thesis_agents.backends import RunAudit
from thesis_agents.canonical.contracts import PreparationRequest
from thesis_agents.canonical.preparation import bytes_digest
from thesis_agents.canonical.session import PreparationSession
from thesis_agents.execution_profiles import RealExecutionProfile
from thesis_agents.mcp.client import MCPClient
from thesis_agents.mcp.shared_client import SharedServicesClient
from thesis_agents.orchestration.artifacts import ArtifactSession
from thesis_agents.strategic.validation_contracts import ValidationProfile
from thesis_agents.telemetry.settings import TelemetryHTTPSettings
from thesis_agents.tools.sbom_http import HTTPSupplyChainTool
from thesis_agents.tools.telemetry_http import HTTPTelemetryTool


class UnconfiguredBackend:
    """A hard error during wiring; never computes a local/mock substitute."""

    def unavailable(self, *args, **kwargs):
        raise RuntimeError("Real backend not connected; local/mock fallback is disabled")

    lookup_vulnerabilities = unavailable
    rank_graph = unavailable
    validate_countermeasure = unavailable
    record_provenance = unavailable


class RealSourceSession(ArtifactSession):
    def __init__(self, case, output_dir, profile, *, model=None):
        blocked = UnconfiguredBackend()
        super().__init__(
            case,
            output_dir,
            mode="camel",
            model=model,
            vulnerability_tool=blocked,
            ranking_tool=blocked,
            semantic_tool=blocked,
            provenance_tool=blocked,
        )
        self._bindings = [b.model_dump(mode="json") for b in profile.preparation_scope.bindings]

    def publish_candidate_strategies(self, payload: str) -> dict:
        """Reject a configured-scope mismatch before an immutable publication."""
        from thesis_agents.schemas import CandidateStrategies, VulnerabilityReport

        report = self.require("vulnerability_report", VulnerabilityReport)
        candidates = CandidateStrategies.model_validate_json(payload)
        if report.vulnerabilities:
            expected = {(b["cve_id"], b["strategy_id"]) for b in self._bindings}
            actual = {
                (cve, candidate.id)
                for candidate in candidates.strategies
                for cve in candidate.addressed_vulnerabilities
            }
            if actual != expected:
                raise ValueError("Publish exactly the configured canonical CVE/strategy bindings")
        return super().publish_candidate_strategies(payload)

    def get_context(self):
        """Read source artifacts and the explicit operator MAS/KG bindings.

        Returns:
            dict: Authoritative source context, including configured candidate identities.
        """
        context = super().get_context()
        context.setdefault("external_inputs", {})["canonical_bindings"] = {
            "origin": "operator_configuration",
            "bindings": copy.deepcopy(self._bindings),
            "instruction": "Candidate IDs/CVEs must exactly cover these MAS/KG pairs; "
            "do not invent or silently omit bindings.",
        }
        return context


@contextmanager
def connect_real_sources(session, settings):
    """Connect actual telemetry/CTI/SBOM adapters; there are no optional mock defaults."""
    from thesis_agents.tools.cti_mcp import CTIVulnerabilityTool, cti_contracts
    from thesis_agents.tools.ubuntu_mcp import UbuntuVulnerabilityTool, ubuntu_contracts
    from thesis_agents.tools.vulnerability_mcp import MCPVulnerabilityTool, lookup_contracts

    root = session.output_dir
    (root / "source-backends.json").write_text(settings.model_dump_json(indent=2) + "\n")
    session.telemetry_tool = HTTPTelemetryTool(
        settings.telemetry, RunAudit(root / "telemetry_events.jsonl", session.run_id)
    )
    session.supply_chain_tool = HTTPSupplyChainTool(
        settings.countermeasure_input, RunAudit(root / "supply_chain_events.jsonl", session.run_id)
    )
    adapter = settings.vulnerability_adapter
    contracts = (
        ubuntu_contracts()
        if adapter == "ubuntu-package-v1"
        else (cti_contracts() if adapter == "cve2owl-v1" else lookup_contracts())
    )
    with MCPClient(
        settings.vulnerability,
        contracts=contracts,
        audit=RunAudit(root / "mcp_events.jsonl", session.run_id),
        stderr_path=root / "cti.stderr.log",
    ) as client:
        if adapter == "ubuntu-package-v1":
            session.vulnerability_tool = UbuntuVulnerabilityTool(
                client,
                root,
                dataset_sha256=settings.cti_dataset_sha256,
                sources_sha256=settings.ubuntu_sources_sha256,
            )
        elif adapter == "cve2owl-v1":
            session.vulnerability_tool = CTIVulnerabilityTool(
                client, root, expected_dataset_sha256=settings.cti_dataset_sha256
            )
        else:
            session.vulnerability_tool = MCPVulnerabilityTool(client)
        yield


def preflight_real(profile, case):
    """Local/configuration checks only; no live availability probe or implicit deployment."""
    if not isinstance(profile.sources.telemetry, TelemetryHTTPSettings):
        raise ValueError("Real mode requires acquired telemetry")
    if set(case.available_capabilities) != set(profile.validation.available_capabilities) or set(
        case.prohibited_actions
    ) != set(profile.validation.prohibited_actions):
        raise ValueError("Input and validation profile specify different operational policies")
    prep = profile.preparation
    if not prep.python.is_file() or not os.access(prep.python, os.X_OK):
        raise ValueError("Configured preparation Python executable is missing")
    with prep.source_ontology.open("rb") as stream:
        source_digest = file_digest(stream, "sha256").hexdigest()
    if source_digest != prep.source_ontology_sha256:
        raise ValueError("Configured source ontology digest differs")
    module = prep.repository / "app/semantic_preparation"
    if (
        bytes_digest((module / "installation-manifest.json").read_bytes())
        != prep.generator_manifest_sha256
    ):
        raise ValueError("Configured generator manifest differs")
    branch = subprocess.check_output(
        ["git", "branch", "--show-current"], cwd=prep.repository, text=True
    ).strip()
    if branch != "costa-thesis":
        raise ValueError("External generator must be on costa-thesis")
    for service in (profile.sources.telemetry, profile.sources.countermeasure_input):
        service.headers()
    connection = profile.sources.vulnerability
    if hasattr(connection, "environment"):
        connection.environment()
    else:
        connection.headers()
    profile.shared.connection.environment()


def run_real(profile, case, output_dir, backend_factory, *, workflow="pipeline", model=None):
    """Execute the artifact DAG through shared finalization, with no backend fallback."""
    from thesis_agents.agents.contracts import AGENT_CONTRACTS
    from thesis_agents.canonical.agent import run_preparation_agent
    from thesis_agents.orchestration.artifacts import ARTIFACT_SCHEMAS
    from thesis_agents.orchestration.native_dag import NativeArtifactDAG
    from thesis_agents.orchestration.workforce import run_camel_sources
    from thesis_agents.strategic.agent import run_native_strategic_agent
    from thesis_agents.strategic.finalization_agent import run_finalization_agent
    from thesis_agents.strategic.finalization_session import NativeFinalizationSession
    from thesis_agents.strategic.selection_agent import run_selection_agent
    from thesis_agents.strategic.selection_session import NativeSelectionSession
    from thesis_agents.strategic.session import NativeStrategicSession
    from thesis_agents.strategic.validation_agent import run_validation_agent
    from thesis_agents.strategic.validation_session import NativeValidationSession

    profile = RealExecutionProfile.model_validate(profile.model_dump())
    preflight_real(profile, case)
    root = Path(output_dir)
    root.mkdir(parents=True, exist_ok=False)
    (root / "real-profile.json").write_text(profile.model_dump_json(indent=2) + "\n")
    (root / "input.json").write_text(case.model_dump_json(indent=2) + "\n")
    state = {
        "backend_mode": "real",
        "inference_mode": "camel",
        "status": "running",
        "workflow": workflow,
        "completed_stages": [],
        "recommendation": "pending",
        "shared_finalization": "pending",
        "deployment_verified": False,
        "action_execution": "not_performed",
    }

    def save(stage=None):
        if stage:
            state["completed_stages"].append(stage)
        (root / "execution.json").write_text(json.dumps(state, indent=2) + "\n")

    save()
    try:
        sources = RealSourceSession(case, root / "sources", profile, model=model)
        state["run_id"] = sources.run_id
        dag = NativeArtifactDAG(root, run_id=sources.run_id, workflow=workflow)
        save()

        def source_validator(name):
            snapshot = []

            def validate():
                model = sources.require(name, ARTIFACT_SCHEMAS[name])
                raw = (sources.output_dir / f"{name}.json").read_bytes()
                if json.loads(raw) != model.model_dump(mode="json"):
                    raise ValueError("Source publication differs from its producer artifact")
                if snapshot and raw != snapshot[0]:
                    raise ValueError("Source publication changed after DAG completion")
                if not snapshot:
                    snapshot.append(raw)

            return validate

        source_checks = [(c.task_id, source_validator(c.outputs[0])) for c in AGENT_CONTRACTS[:3]]
        try:
            with connect_real_sources(sources, profile.sources):
                evidence, report, candidates = run_camel_sources(
                    sources, backend_factory, workflow=workflow
                )
        except BaseException:
            dag.fail_sources(source_checks)
            raise
        for task_id, validator in source_checks:
            dag.complete_source(task_id, validator)
        save("sources")
        if not candidates.strategies:
            outcome = (
                "no_findings" if report.lookup_status == "no_findings" else "insufficient_evidence"
            )
            dag.skip_native(outcome)
            state.update(
                status="assessment_completed",
                outcome=outcome,
                recommendation="not_applicable",
                shared_finalization="not_applicable",
            )
            save()
            return state

        sessions = {}

        def execute(task_id, stage, constructor, runner):
            def operation():
                sessions[stage] = constructor()
                return runner(sessions[stage], backend_factory())

            result = dag.execute(task_id, operation, lambda: sessions[stage].assert_complete())
            save(stage)
            return result

        def prepare():
            request = PreparationRequest(
                run_id=sources.run_id,
                asset_id=evidence.service_name,
                input_digests={
                    name: bytes_digest((sources.output_dir / f"{name}.json").read_bytes())
                    for name in ("runtime_evidence", "vulnerability_report", "candidate_strategies")
                },
                **profile.preparation_scope.model_dump(),
            )
            return PreparationSession(
                sources.output_dir, root / "preparation", request, profile.preparation
            )

        execute("semantic_preparation", "preparation", prepare, run_preparation_agent)
        audit = RunAudit(root / "shared_mcp_events.jsonl", sources.run_id)
        with ExitStack() as stack:

            def rank():
                shared = stack.enter_context(
                    SharedServicesClient(
                        profile.shared,
                        audit=audit,
                        stderr_path=root / "shared.stderr.log",
                        finalization=True,
                    )
                )
                sessions["shared"] = shared
                return NativeStrategicSession(
                    root / "preparation", root / "strategic", profile.ranking, shared
                )

            execute("strategic_native_ranking", "ranking", rank, run_native_strategic_agent)

            def validate():
                validation_profile = ValidationProfile(
                    run_id=sources.run_id,
                    asset_id=evidence.service_name,
                    ranking_sha256=bytes_digest(
                        (root / "strategic/native_strategic_ranking.json").read_bytes()
                    ),
                    **profile.validation.model_dump(),
                )
                return NativeValidationSession(
                    root / "strategic", root / "validation", validation_profile, sessions["shared"]
                )

            execute("strategic_native_validation", "validation", validate, run_validation_agent)
            recommendation = execute(
                "strategic_native_selection",
                "recommendation",
                lambda: NativeSelectionSession(root / "validation", root / "recommendation"),
                run_selection_agent,
            )
            execute(
                "strategic_native_finalization",
                "finalization",
                lambda: NativeFinalizationSession(
                    root / "recommendation", root / "finalization", sessions["shared"]
                ),
                run_finalization_agent,
            )
        dag.assert_complete()
        state.update(
            status="dry_run_completed",
            recommendation="published",
            shared_finalization="completed",
            finalization_file="finalization/native_strategic_finalization.json",
            verification_scope="backend_reported_commit_and_readback",
            outcomes_by_cve={r.cve_id: r.outcome for r in recommendation.results},
            recommendation_file="recommendation/native_strategic_recommendation.json",
        )
        save()
        return state
    except BaseException as exc:
        state.update(status="failed", error_type=type(exc).__name__)
        save()
        raise
