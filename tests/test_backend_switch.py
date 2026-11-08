"""One launcher, explicit backend switch. Real-mode integration uses synthetic services."""

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import httpx
import pytest
import test_canonical_preparation as preparation_tests
import test_telemetry as telemetry_tests
from test_camel_integration import ScriptedToolModel
from test_mcp_stdio import assert_child_stopped, stdio_settings

from services.otel_gateway.server import read_snapshot
from services.sbom_gateway.server import Gateway
from thesis_agents.backends import BackendSettings
from thesis_agents.execution_profiles import RealExecutionProfile
from thesis_agents.execution_runtime import RealSourceSession, connect_real_sources
from thesis_agents.fixtures import fixture_candidates, fixture_evidence
from thesis_agents.main import main
from thesis_agents.mcp.client import MCPError
from thesis_agents.mcp.shared_client import SharedMCPProfile
from thesis_agents.orchestration.artifacts import ArtifactSession
from thesis_agents.orchestration.publication_tools import PublicationTools
from thesis_agents.schemas.supply_chain import AssetBinding, SupplyChainQuery
from thesis_agents.schemas.telemetry_source import TelemetryInput, TelemetryQuery

canonical_case = preparation_tests.canonical_case
ROOT = Path(__file__).resolve().parents[1]


@pytest.mark.mcp_http
@pytest.mark.parametrize("correct_digest", [True, False])
def test_native_source_wiring_checks_cti_dataset_over_mcp(
    http_server, case, tmp_path, correct_digest
):
    """Exercise real source wiring with a declared mock HTTP service and pinned data."""
    case.package_name = "Apache Log4j Core"
    settings = BackendSettings(
        vulnerability_adapter="cve2owl-v1",
        vulnerability={
            "transport": "mcp",
            "url": http_server(kind="cti"),
            "expected_kind": "mock",
        },
        cti_dataset_sha256=("a" if correct_digest else "b") * 64,
    )
    session = ArtifactSession(case, tmp_path / "sources", mode="camel", model="no-inference")
    session.publish_runtime_evidence(fixture_evidence(session).model_dump_json())
    with connect_real_sources(session, settings):
        if not correct_digest:
            with pytest.raises(MCPError):
                session.lookup_vulnerabilities()
            assert "vulnerability_report" not in session.get_context()["artifacts"]
        else:
            result = session.lookup_vulnerabilities()
            assert result["lookup_status"] == "matched"
            assert result["cti"]["backend_kind"] == "mock"
            assert result["cti"]["dataset_sha256"] == "a" * 64
            assert {row["cve_id"] for row in result["vulnerabilities"]} == {
                "CVE-2025-68161",
                "CVE-2026-34477",
                "CVE-2026-34480",
            }


@pytest.mark.mcp_http
@pytest.mark.parametrize("tampered", [False, True])
def test_acquired_cti_publication_is_argumentless_and_checks_snapshot(
    http_server, case, tmp_path, tampered
):
    case.package_name = "Apache Log4j Core"
    settings = BackendSettings(
        vulnerability_adapter="cve2owl-v1",
        vulnerability={"transport": "mcp", "url": http_server(kind="cti"), "expected_kind": "mock"},
        cti_dataset_sha256="a" * 64,
    )
    session = ArtifactSession(case, tmp_path / "sources", mode="camel", model="no-inference")
    session.publish_runtime_evidence(fixture_evidence(session).model_dump_json())
    with connect_real_sources(session, settings):
        tool = PublicationTools(session).resolve("publish_vulnerability_report")
        assert not tool.get_openai_tool_schema()["function"]["parameters"].get("properties")
        with pytest.raises(ValueError, match="lookup_vulnerabilities"):
            tool()
        assert not (session.output_dir / "vulnerability_report.json").exists()
        report = session.lookup_vulnerabilities()
        if tampered:
            snapshot = session.output_dir / "cti_assessment.json"
            data = json.loads(snapshot.read_bytes())
            data["software"]["product"] = "altered"
            snapshot.write_text(json.dumps(data))
            with pytest.raises(ValueError):
                tool()
            assert not (session.output_dir / "vulnerability_report.json").exists()
        else:
            assert tool() == report
            before = (session.output_dir / "vulnerability_report.json").read_bytes()
            assert tool() == report
            assert (session.output_dir / "vulnerability_report.json").read_bytes() == before


def example():
    return json.loads((ROOT / "config/backends.real.example.json").read_bytes())


def test_real_candidate_binding_error_is_recoverable_before_publication(case, tmp_path, session):
    configured = RealSourceSession(
        case, tmp_path / "configured", RealExecutionProfile.model_validate(example())
    )
    configured.vulnerability_tool = session.vulnerability_tool  # declared local fixture only
    configured.publish_runtime_evidence(fixture_evidence(configured).model_dump_json())
    report = configured.lookup_vulnerabilities()
    configured.publish_vulnerability_report(json.dumps(report))
    candidates = fixture_candidates([f["cve_id"] for f in report["vulnerabilities"]])
    invalid = candidates.model_copy(deep=True)
    invalid.strategies[0].id = "UNCONFIGURED"
    with pytest.raises(ValueError, match="configured canonical"):
        configured.publish_candidate_strategies(invalid.model_dump_json())
    assert not (configured.output_dir / "candidate_strategies.json").exists()
    configured.publish_candidate_strategies(candidates.model_dump_json())
    assert (configured.output_dir / "candidate_strategies.json").exists()


@pytest.mark.parametrize(
    "field", ["cti", "shared", "osv", "sbom", "snapshot", "binding", "duplicates"]
)
def test_real_profile_cannot_select_mock_or_inconsistent_services(field):
    payload = example()
    if field == "cti":
        payload["sources"]["vulnerability"]["expected_kind"] = "mock"
    if field == "shared":
        payload["shared"]["connection"]["expected_kind"] = "mock"
    if field == "osv":
        payload["sources"]["countermeasure_input"]["expected_kind"] = "mock"
    if field == "sbom":
        payload["sources"]["countermeasure_input"]["sbom_kind"] = "demo"
    if field == "snapshot":
        payload["ranking"]["knowledge_snapshot_id"] = "other"
    if field == "binding":
        payload["validation"]["bindings"].pop()
    if field == "duplicates":
        payload["preparation_scope"]["bindings"].append(payload["preparation_scope"]["bindings"][0])
    with pytest.raises(ValueError):
        RealExecutionProfile.model_validate(payload)


@pytest.mark.parametrize("mode", ["mockup", None])
def test_mockup_switch_is_local_and_independent_of_inference(tmp_path, mode):
    output = tmp_path / "mock"
    args = ["--mode", "fixtures", "--output", str(output)]
    if mode:
        args += ["--backend-mode", mode]
    assert main(args) == 0
    execution = json.loads((output / "execution.json").read_bytes())
    assert execution["backend_mode"] == "mockup" and execution["inference_mode"] == "fixtures"
    assert (
        json.loads((output / "final_decision.json").read_bytes())["selected_strategy_id"]
        == "S_UPGRADE"
    )


def test_explicit_mockup_rejects_remote_profile_before_output(tmp_path):
    assert (
        main(
            [
                "--backend-mode",
                "mockup",
                "--backends",
                str(ROOT / "config/backends.mcp-stdio-mock.json"),
                "--mode",
                "fixtures",
                "--output",
                str(tmp_path / "out"),
            ]
        )
        == 1
    )
    assert not (tmp_path / "out").exists()


def test_real_requires_configuration_and_forbids_fixture_execution(tmp_path):
    assert (
        main(["--backend-mode", "real", "--mode", "fixtures", "--output", str(tmp_path / "out")])
        == 1
    )
    assert main(["--backend-mode", "real", "--output", str(tmp_path / "out")]) == 1
    assert not (tmp_path / "out").exists()


@pytest.fixture
def real_case(canonical_case, tmp_path):
    source, request, preparation = canonical_case
    case = TelemetryInput(
        service_name=request.asset_id,
        service_instance_id="switch-fixture",
        package_name="log4j-core",
        start_time="2026-01-01T00:00:00Z",
        end_time="2026-01-01T00:01:00Z",
        available_capabilities=[],
        prohibited_actions=[],
    )
    export = tmp_path / "otel.json"
    telemetry_tests.write_export(export, telemetry_tests.otel_document(case))
    binding = AssetBinding(
        service_name=case.service_name,
        runtime_package=case.package_name,
        component_ref="log4j-core",
    )
    gateway = Gateway(
        ROOT / "services/sbom_gateway/data/log4j-demo.cdx.json",
        binding,
        "switch-sbom",
        "provided",
        "live",
        "https://api.osv.dev/v1/query",
    )

    class Handler(BaseHTTPRequestHandler):
        fault = None

        def log_message(self, *args):
            pass

        def do_POST(self):
            body = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            if self.path == "/telemetry":
                data = read_snapshot(
                    export,
                    TelemetryQuery.model_validate(body),
                    source_id="switch-otel",
                    acquisition="recorded",
                )
            elif self.path == "/supply":
                with httpx.Client(
                    transport=httpx.MockTransport(lambda r: httpx.Response(200, json={}))
                ) as http:
                    data = gateway.assess(SupplyChainQuery.model_validate(body), http)
            else:
                self.send_error(404)
                return
            encoded = data.model_dump_json().encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(encoded)))
            self.end_headers()
            self.wfile.write(encoded)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f"http://127.0.0.1:{server.server_port}"
    lookup = stdio_settings(tmp_path, kind="lookup-real-fixture").model_dump(mode="json")
    lookup.update(expected_kind="real")
    lookup["args"][2] = str(tmp_path / "lookup.pid")
    shared = stdio_settings(tmp_path, kind="shared").model_dump(mode="json")
    shared.update(expected_kind="real")
    shared["args"][2] = str(tmp_path / "shared.pid")
    payload = dict(
        contract="real-execution-v1",
        sources={
            "telemetry": {
                "url": url + "/telemetry",
                "source_id": "switch-otel",
                "acquisition": "recorded",
            },
            "vulnerability": lookup,
            "vulnerability_adapter": "lookup-v1",
            "countermeasure_input": {
                "url": url + "/supply",
                "expected_kind": "live",
                "source_id": "switch-sbom",
                "sbom_kind": "provided",
            },
        },
        preparation=preparation.model_dump(mode="json"),
        preparation_scope=request.model_dump(mode="json", include={"assessments", "bindings"}),
        shared=SharedMCPProfile.model_validate({"connection": shared}).model_dump(mode="json"),
        ranking={
            "tenant_id": "fixture",
            "knowledge_snapshot_id": preparation.knowledge_snapshot_id,
            "knowledge_snapshot_digest": "sha256:" + "b" * 64,
            "ontology_digest": "sha256:" + "a" * 64,
        },
        validation={
            "ontology_key": "fixture-tbox",
            "asset_iri": "urn:switch:asset",
            "bindings": [
                {**b.model_dump(), "countermeasure_iri": "urn:switch:" + b.ontology_individual}
                for b in request.bindings
            ],
            "available_capabilities": [],
            "prohibited_actions": [],
            "constraint_mappings": [],
            "policy_source": "Explicit synthetic operator policy",
        },
    )
    RealExecutionProfile.model_validate(payload)
    case_path, profile_path = tmp_path / "input.json", tmp_path / "profile.json"
    case_path.write_text(case.model_dump_json())
    profile_path.write_text(json.dumps(payload))
    try:
        yield case_path, profile_path, payload
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)


@pytest.fixture
def scripted_models(monkeypatch):
    from thesis_agents.canonical.session import PreparationSession
    from thesis_agents.config import ModelSettings
    from thesis_agents.strategic.finalization_session import NativeFinalizationSession
    from thesis_agents.strategic.selection_session import NativeSelectionSession
    from thesis_agents.strategic.session import NativeStrategicSession
    from thesis_agents.strategic.validation_session import NativeValidationSession

    current = []
    original = ArtifactSession.__init__

    def init(self, *args, **kwargs):
        original(self, *args, **kwargs)
        current[:] = [self]

    monkeypatch.setattr(ArtifactSession, "__init__", init)

    def capture_native(cls):
        original_native = cls.__init__

        def init_native(self, *args, **kwargs):
            original_native(self, *args, **kwargs)
            current[:] = [self]

        monkeypatch.setattr(cls, "__init__", init_native)

    for cls in (
        PreparationSession,
        NativeStrategicSession,
        NativeValidationSession,
        NativeSelectionSession,
        NativeFinalizationSession,
    ):
        capture_native(cls)

    class Model(ScriptedToolModel):
        def _run(self, messages, response_format=None, tools=None):
            if not isinstance(self.session, ArtifactSession):
                names = {t["function"]["name"] for t in tools or []}
                if not names:
                    return self._completion(content='{"content":"Published","failed":false}')
                assert len(names) == 1
                name = names.pop()
                if name == "get_context" or isinstance(self.session, PreparationSession):
                    arguments = {}
                else:
                    arguments = {
                        k: v for k, v in self.session.next_operation().items() if k != "tool"
                    }
                self.tool_calls.append(name)
                return self._completion(
                    tool_calls=[
                        {
                            "id": f"native-{len(messages)}",
                            "type": "function",
                            "function": {"name": name, "arguments": json.dumps(arguments)},
                        }
                    ]
                )
            if not tools and "Coordinate exactly" not in str(messages[0].get("content", "")):
                return self._completion(content='{"content":"Published","failed":false}')
            return super()._run(messages, response_format=response_format, tools=tools)

    class Settings:
        model = "scripted-fixture-only"

        def create_backend(self):
            return Model(current[0])

    monkeypatch.setattr(ModelSettings, "from_env", lambda: Settings())


def args_for(real_case, output):
    case, profile, _ = real_case
    return [
        "--backend-mode",
        "real",
        "--backends",
        str(profile),
        "--input",
        str(case),
        "--output",
        str(output),
    ]


@pytest.mark.mcp_http
@pytest.mark.parametrize(
    "scenario,selected,outcome",
    [
        ("missing", None, "requires_prerequisites"),
        ("accepted", "S_UPGRADE", "recommended"),
        ("alternative", "S_ISOLATE", "recommended"),
        ("review", None, "requires_review"),
        ("rejected", None, "no_valid_strategy"),
    ],
)
def test_one_launcher_real_routes_all_native_stages_without_instantiating_mocks(
    real_case, scripted_models, tmp_path, monkeypatch, scenario, selected, outcome
):
    import thesis_agents.orchestration.artifacts as artifacts
    from thesis_agents.fixtures import fixture_candidates
    from thesis_agents.mcp.operational_contracts import ACTION_REQUIREMENTS

    case_path, profile_path, profile = real_case
    case = json.loads(case_path.read_bytes())
    if scenario != "missing":
        profile["validation"]["available_capabilities"] = sorted(
            {c for caps in ACTION_REQUIREMENTS.values() for c in caps} | {"operator_review"}
        )
        if scenario != "review":
            profile["validation"]["constraint_mappings"] = [
                {
                    "strategy_id": c.id,
                    "constraint": constraint,
                    "required_capabilities": ["operator_review"],
                }
                for c in fixture_candidates(["CVE-2021-44228"]).strategies
                for constraint in c.constraints
            ]
        profile["validation"]["prohibited_actions"] = (
            ["upgrade"]
            if scenario == "alternative"
            else list(ACTION_REQUIREMENTS)
            if scenario == "rejected"
            else []
        )
    for key in ("available_capabilities", "prohibited_actions"):
        case[key] = profile["validation"][key]
    case_path.write_text(json.dumps(case))
    profile_path.write_text(json.dumps(profile))

    def forbidden(*args, **kwargs):
        raise AssertionError("Mock instantiated in real mode")

    for name in (
        "MockVulnerabilityTool",
        "MockRankingTool",
        "MockSemanticTool",
        "MockProvenanceTool",
    ):
        monkeypatch.setattr(artifacts, name, forbidden)
    output = tmp_path / "real-run"
    assert main(args_for(real_case, output)) == 0
    state = json.loads((output / "execution.json").read_bytes())
    assert state["backend_mode"] == "real" and state["status"] == "dry_run_completed"
    assert state["completed_stages"] == [
        "sources",
        "preparation",
        "ranking",
        "validation",
        "recommendation",
        "finalization",
    ]
    assert state["recommendation"] == "published" and state["shared_finalization"] == "completed"
    dag = json.loads((output / "dag.json").read_bytes())
    assert len(dag["nodes"]) == 8
    assert all(n["status"] == "completed" for n in dag["nodes"].values())
    recommendation = json.loads((output / state["recommendation_file"]).read_bytes())
    assert recommendation["results"][0]["selected_strategy_id"] == selected
    assert recommendation["results"][0]["outcome"] == outcome
    validation = json.loads((output / "validation/native_strategic_validation.json").read_bytes())
    assert len(validation["attempts"]) == 4
    if scenario == "missing":
        assert all(
            a["response"]["effectiveStatus"] == "requires_prerequisites"
            for a in validation["attempts"]
        )
    finalization = json.loads((output / state["finalization_file"]).read_bytes())
    assert finalization["shared_finalization"] == "completed"
    assert finalization["results"][0]["ledger_readback_verified"] is True
    assert finalization["results"][0]["record"]["transaction_id"].startswith("fixture-tx-")
    assert not (output / "sources/final_decision.json").exists()
    assert_child_stopped(tmp_path / "lookup.pid")
    assert_child_stopped(tmp_path / "shared.pid")


@pytest.mark.mcp_http
def test_real_validation_failure_blocks_selection_and_keeps_attempt_diagnostics(
    real_case, scripted_models, tmp_path
):
    _, profile_path, profile = real_case
    profile["shared"]["connection"]["args"][-1] = "operational-digest"
    profile_path.write_text(json.dumps(profile))
    output = tmp_path / "validation-failed"
    assert main(args_for(real_case, output)) == 1
    state = json.loads((output / "execution.json").read_bytes())
    assert state["completed_stages"] == ["sources", "preparation", "ranking"]
    assert state["recommendation"] == "pending" and state["status"] == "failed"
    dag = json.loads((output / "dag.json").read_bytes())
    assert dag["nodes"]["strategic_native_validation"]["status"] == "failed"
    assert dag["nodes"]["strategic_native_selection"]["status"] == "blocked"
    assert list((output / "validation/attempts").rglob("*.request.json"))
    assert not (output / "recommendation").exists()
    assert_child_stopped(tmp_path / "shared.pid")


@pytest.mark.mcp_http
def test_real_generator_failure_blocks_ranking_before_shared_process(
    real_case, scripted_models, tmp_path, monkeypatch
):
    from thesis_agents.canonical.preparation import ExternalPreparationTool

    def failure(*args):
        raise RuntimeError("Synthetic generator failure")

    monkeypatch.setattr(ExternalPreparationTool, "prepare", failure)
    output = tmp_path / "preparation-failed"
    assert main(args_for(real_case, output)) == 1
    dag = json.loads((output / "dag.json").read_bytes())
    assert dag["nodes"]["semantic_preparation"]["status"] == "failed"
    assert dag["nodes"]["strategic_native_ranking"]["status"] == "blocked"
    assert not (tmp_path / "shared.pid").exists()


@pytest.mark.mcp_http
def test_real_remote_failure_never_falls_back_to_mockup(real_case, scripted_models, tmp_path):
    case_path, profile_path, profile = real_case
    profile["shared"]["connection"]["args"][-1] = "disconnect"
    profile_path.write_text(json.dumps(profile))
    output = tmp_path / "failed"
    assert main(args_for(real_case, output)) == 1
    state = json.loads((output / "execution.json").read_bytes())
    assert state["status"] == "failed" and state["completed_stages"] == ["sources", "preparation"]
    dag = json.loads((output / "dag.json").read_bytes())
    assert dag["nodes"]["strategic_native_ranking"]["status"] == "failed"
    assert dag["nodes"]["strategic_native_validation"]["status"] == "blocked"
    assert dag["nodes"]["strategic_native_selection"]["status"] == "blocked"
    assert not (output / "validation").exists() and not (output / "final_decision.json").exists()
    assert_child_stopped(tmp_path / "shared.pid")


@pytest.mark.mcp_http
def test_real_empty_assessment_is_a_bounded_outcome_without_ranking(
    real_case, scripted_models, tmp_path
):
    case_path, profile_path, profile = real_case
    profile["sources"]["vulnerability"]["args"][-1] = "unsupported"
    profile_path.write_text(json.dumps(profile))
    output = tmp_path / "no-findings"
    assert main(args_for(real_case, output)) == 0
    state = json.loads((output / "execution.json").read_bytes())
    assert state["status"] == "assessment_completed" and state["outcome"] == "insufficient_evidence"
    assert state["recommendation"] == "not_applicable" and not (tmp_path / "shared.pid").exists()
    assert state["shared_finalization"] == "not_applicable"
    dag = json.loads((output / "dag.json").read_bytes())
    assert all(
        n["status"] == "skipped"
        for k, n in dag["nodes"].items()
        if k.startswith(("semantic_", "strategic_"))
    )


@pytest.mark.mcp_http
@pytest.mark.parametrize("change", ["ontology", "branch", "policy"])
def test_real_local_preflight_fails_before_remote_process_or_output(
    real_case, scripted_models, tmp_path, change
):
    import subprocess

    case_path, profile_path, profile = real_case
    if change == "ontology":
        Path(profile["preparation"]["source_ontology"]).write_text("changed")
    if change == "branch":
        subprocess.run(
            ["git", "symbolic-ref", "HEAD", "refs/heads/main"],
            cwd=profile["preparation"]["repository"],
            check=True,
        )
    if change == "policy":
        profile["validation"]["available_capabilities"] = ["monitoring"]
    profile_path.write_text(json.dumps(profile))
    output = tmp_path / "invalid"
    assert main(args_for(real_case, output)) == 1
    assert not output.exists() and not (tmp_path / "lookup.pid").exists()


@pytest.mark.mcp_http
@pytest.mark.parametrize(
    "fault", ["finalization-commit", "finalization-digest", "finalization-readback"]
)
def test_shared_finalization_failure_does_not_publish_success(
    real_case, scripted_models, tmp_path, fault
):
    _, profile_path, profile = real_case
    profile["shared"]["connection"]["args"][-1] = fault
    profile_path.write_text(json.dumps(profile))
    output = tmp_path / "finalization-failed"
    assert main(args_for(real_case, output)) == 1
    state = json.loads((output / "execution.json").read_bytes())
    assert state["status"] == "failed" and state["shared_finalization"] == "pending"
    assert state["completed_stages"][-1] == "recommendation"
    dag = json.loads((output / "dag.json").read_bytes())
    assert dag["nodes"]["strategic_native_selection"]["status"] == "completed"
    assert dag["nodes"]["strategic_native_finalization"]["status"] == "failed"
    assert not (output / "finalization/native_strategic_finalization.json").exists()
    assert list((output / "finalization/native").rglob("document.json"))
    assert_child_stopped(tmp_path / "shared.pid")
