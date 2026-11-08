"""IRI/policy nei tool reali CAMEL/stdio; SaaS simulato, nessuna prova Tiny-ME live."""

import copy
import json
from concurrent.futures import ThreadPoolExecutor

import pytest
import test_native_strategic as native_tests
from test_camel_integration import ScriptedToolModel
from test_mcp_stdio import assert_child_stopped
from test_native_strategic import complete, connection, settings

from thesis_agents.canonical.preparation import bytes_digest
from thesis_agents.mcp.client import MCPError
from thesis_agents.mcp.operational_contracts import ACTION_REQUIREMENTS, OperationalContext
from thesis_agents.strategic.session import NativeStrategicSession
from thesis_agents.strategic.validation_agent import build_validation_agent, run_validation_agent
from thesis_agents.strategic.validation_contracts import ValidationProfile
from thesis_agents.strategic.validation_session import NativeValidationSession

canonical_prepared = native_tests.prepared


@pytest.fixture
def ranked(canonical_prepared, tmp_path):
    client = connection(tmp_path)
    session = NativeStrategicSession(canonical_prepared, tmp_path / "ranked", settings(), client)
    with client:
        complete(session)
    (tmp_path / "child.pid").unlink()
    return session.output_dir


def profile_for(directory):
    ranking = json.loads((directory / "native_strategic_ranking.json").read_bytes())
    candidates = json.loads(
        (directory / "preparation/inputs/candidate_strategies.json").read_bytes()
    )
    mappings = [
        {
            "strategy_id": candidate["id"],
            "constraint": constraint,
            "required_capabilities": [f"approved_{candidate['id']}"],
        }
        for candidate in candidates["strategies"]
        for constraint in candidate["constraints"]
    ]
    capabilities = set(cap for caps in ACTION_REQUIREMENTS.values() for cap in caps)
    capabilities |= {
        cap for candidate in candidates["strategies"] for cap in candidate["prerequisites"]
    }
    capabilities |= {cap for m in mappings for cap in m["required_capabilities"]}
    return ValidationProfile(
        run_id=ranking["run_id"],
        asset_id=ranking["asset_id"],
        ranking_sha256=bytes_digest((directory / "native_strategic_ranking.json").read_bytes()),
        ontology_key="fixture-tbox",
        asset_iri="urn:test:asset",
        bindings=[
            {**binding, "countermeasure_iri": "urn:test:" + binding["ontology_individual"]}
            for result in ranking["results"]
            for binding in result["bindings"]
        ],
        available_capabilities=sorted(capabilities),
        prohibited_actions=[],
        constraint_mappings=mappings,
        policy_source="Synthetic operator policy; not telemetry",
    )


def validate_all(session):
    session.get_context()
    while operation := session.next_operation():
        arguments = dict(operation)
        getattr(session, arguments.pop("tool"))(**arguments)
    return session.assert_complete()


def test_complete_native_validation_preserves_context_iris_and_sources(ranked, tmp_path):
    client = connection(tmp_path)
    profile = profile_for(ranked)
    session = NativeValidationSession(ranked, tmp_path / "validated", profile, client)
    with client:
        artifact = validate_all(session)
        assert session.publish_native_validation() == artifact.model_dump(
            mode="json", by_alias=True
        )
    assert len(artifact.attempts) == 8
    ranking = json.loads((ranked / "native_strategic_ranking.json").read_bytes())
    assert [(a.cve_id, a.ontology_individual) for a in artifact.attempts] == [
        (r["cve_id"], row["id"])
        for r in ranking["results"]
        for row in r["ranking"]["rankedStrategies"]
    ]
    for attempt in artifact.attempts:
        context = attempt.request.operational_context
        assert attempt.response.status == attempt.response.effective_status == "accepted"
        assert attempt.response.operational.evaluator == "saas_operational_policy"
        assert attempt.response.reasoning.resource_iri == profile.asset_iri
        assert attempt.request.countermeasure_iri.endswith(attempt.ontology_individual)
        assert context.run_id == artifact.run_id and context.asset_id == artifact.asset_id
        assert context.constraints and context.constraint_mappings
    assert artifact.recommendation == artifact.shared_finalization == "pending"
    assert artifact.deployment_verified is False and artifact.action_execution == "not_performed"
    assert_child_stopped(tmp_path / "child.pid")


@pytest.mark.parametrize(
    "scenario,status",
    [
        ("missing", "requires_prerequisites"),
        ("prohibited", "rejected"),
        ("unmapped", "requires_review"),
    ],
)
def test_operational_verdict_cannot_be_overridden_by_native_acceptance(
    ranked, tmp_path, scenario, status
):
    profile = profile_for(ranked)
    if scenario == "missing":
        profile.available_capabilities = []
    if scenario == "prohibited":
        profile.prohibited_actions = list(ACTION_REQUIREMENTS)
    if scenario == "unmapped":
        profile.constraint_mappings = []
    client = connection(tmp_path)
    session = NativeValidationSession(ranked, tmp_path / "validated", profile, client)
    with client:
        artifact = validate_all(session)
    assert all(a.response.status == "accepted" and a.response.valid for a in artifact.attempts)
    assert {a.response.effective_status for a in artifact.attempts} == {status}


@pytest.mark.parametrize(
    "fault,status",
    [("semantic-needs", "requires_prerequisites"), ("semantic-rejected", "rejected")],
)
def test_native_conditions_remain_distinct_from_operational_acceptance(
    ranked, tmp_path, fault, status
):
    client = connection(tmp_path, fault)
    session = NativeValidationSession(ranked, tmp_path / "validated", profile_for(ranked), client)
    with client:
        artifact = validate_all(session)
    assert {a.response.effective_status for a in artifact.attempts} == {status}
    assert {a.response.operational.status for a in artifact.attempts} == {"accepted"}


@pytest.mark.parametrize(
    "change", ["run", "asset", "ranking-digest", "missing-binding", "kg-id", "foreign-constraint"]
)
def test_bad_profiles_fail_before_startup_or_output(ranked, tmp_path, change):
    profile = profile_for(ranked)
    if change == "run":
        profile.run_id = "other"
    if change == "asset":
        profile.asset_id = "other"
    if change == "ranking-digest":
        profile.ranking_sha256 = "0" * 64
    if change == "missing-binding":
        profile.bindings.pop()
    if change == "kg-id":
        profile.bindings[0].ontology_individual = "Unknown"
    if change == "foreign-constraint":
        profile.constraint_mappings[0].constraint = "Invented caveat"
    with pytest.raises(ValueError):
        NativeValidationSession(ranked, tmp_path / "validated", profile, connection(tmp_path))
    assert not (tmp_path / "validated").exists() and not (tmp_path / "child.pid").exists()


@pytest.mark.parametrize(
    "iri",
    [":Asset", "Asset", "http://", "urn:", "urn:test:a b", "https://user:password@example.org/a"],
)
def test_relative_ambiguous_or_credential_iris_rejected(ranked, iri):
    payload = profile_for(ranked).model_dump(mode="json")
    payload["asset_iri"] = iri
    with pytest.raises(ValueError):
        ValidationProfile.model_validate(payload)


@pytest.mark.parametrize(
    "fault",
    [
        "operational-omitted",
        "operational-false-acceptance",
        "operational-digest",
        "wrong-iri",
        "wrong-ontology",
        "tool-error",
        "disconnect",
        "false-acceptance",
    ],
)
def test_inconsistent_backend_or_error_never_publishes_or_falls_back(ranked, tmp_path, fault):
    profile = profile_for(ranked)
    profile.available_capabilities = []
    client = connection(tmp_path, fault)
    session = NativeValidationSession(ranked, tmp_path / "validated", profile, client)
    with client:
        with pytest.raises(MCPError):
            validate_all(session)
        assert session._failed and session.next_operation() is None
        with pytest.raises(ValueError):
            session.publish_native_validation()
    assert not (session.output_dir / "native_strategic_validation.json").exists()
    assert list((session.output_dir / "attempts").rglob("*.request.json"))
    assert_child_stopped(tmp_path / "child.pid")


@pytest.mark.parametrize(
    "file",
    [
        "native_strategic_ranking.json",
        "ranking-profile.json",
        "preparation/canonical_preparation.json",
        "preparation/aln_ontology.owl",
        "native/CVE-2021-44228/get_decision.json",
    ],
)
def test_tampered_rank_checkpoints_rejected_before_calls(ranked, tmp_path, file):
    profile = profile_for(ranked)
    (ranked / file).write_text("{}")
    with pytest.raises(ValueError):
        NativeValidationSession(ranked, tmp_path / "validated", profile, connection(tmp_path))
    assert not (tmp_path / "validated").exists()


def test_existing_files_and_wrong_phase_cannot_be_overwritten(ranked, tmp_path):
    client = connection(tmp_path)
    session = NativeValidationSession(ranked, tmp_path / "validated", profile_for(ranked), client)
    with pytest.raises(FileExistsError):
        NativeValidationSession(ranked, tmp_path / "validated", profile_for(ranked), client)
    with client:
        with pytest.raises(ValueError):
            session.publish_native_validation()
        with pytest.raises(ValueError):
            session.validate_countermeasure("CVE-2021-44228", "INVENTED")
        artifact = validate_all(session)
    stored = session.output_dir / "native_strategic_validation.json"
    payload = artifact.model_dump(mode="json", by_alias=True)
    payload["attempts"].pop()
    stored.write_text(json.dumps(payload))
    with pytest.raises(ValueError):
        session.assert_complete()


@pytest.mark.parametrize("change", ["source", "copy", "profile", "response"])
def test_midrun_tampering_blocks_following_call(ranked, tmp_path, change):
    client = connection(tmp_path)
    session = NativeValidationSession(ranked, tmp_path / "validated", profile_for(ranked), client)
    with client:
        operation = dict(session.next_operation())
        operation.pop("tool")
        session.validate_countermeasure(**operation)
        if change == "source":
            (ranked / "ranking-profile.json").write_text("{}")
        elif change == "copy":
            (session.output_dir / "ranking-input/ranking-profile.json").write_text("{}")
        elif change == "profile":
            session.profile.available_capabilities = []
        else:
            next((session.output_dir / "attempts").rglob("*.json")).write_text("{}")
        operation = dict(session.next_operation())
        operation.pop("tool")
        with pytest.raises(ValueError):
            session.validate_countermeasure(**operation)


def test_duplicate_parallel_validation_calls_cannot_execute_twice(ranked, tmp_path):
    events = []
    client = connection(tmp_path)
    client.client.audit = events.append
    session = NativeValidationSession(ranked, tmp_path / "validated", profile_for(ranked), client)
    operation = dict(session.next_operation())
    operation.pop("tool")
    with client, ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(session.validate_countermeasure, **operation) for _ in range(2)]
        assert sum(f.exception() is None for f in futures) == 1
        assert len([e for e in events if e.get("tool") == "validate_countermeasure"]) == 1


def test_camel_clones_execute_ordered_validations_and_publish(ranked, tmp_path):
    client = connection(tmp_path)
    session = NativeValidationSession(ranked, tmp_path / "validated", profile_for(ranked), client)

    class Model(ScriptedToolModel):
        def _run(self, messages, response_format=None, tools=None):
            names = {t["function"]["name"] for t in tools or []}
            if not names:
                return self._completion(content="Validation checkpoint published")
            name = names.pop()
            args = (
                {}
                if name == "get_context"
                else {k: v for k, v in session.next_operation().items() if k != "tool"}
            )
            self.tool_calls.append(name)
            return self._completion(
                tool_calls=[
                    {
                        "id": f"call-{len(self.tool_calls)}",
                        "type": "function",
                        "function": {"name": name, "arguments": json.dumps(args)},
                    }
                ]
            )

    model = Model(session)
    clone = build_validation_agent(session, model).clone().clone()
    assert clone.tool_policy.next_tool() == "get_context"
    with client:
        clone.step("Validate all required strategies")
        artifact = session.assert_complete()
    assert len(artifact.attempts) == 8
    assert model.tool_calls == ["get_context"] + ["validate_countermeasure"] * 8 + [
        "publish_native_validation"
    ]


def test_prose_cannot_publish_and_cli_preserves_outputs(ranked, tmp_path, capsys):
    from thesis_agents.strategic.validation import main

    class Model(ScriptedToolModel):
        def _run(self, messages, response_format=None, tools=None):
            return self._completion(content="Everything validated")

    client = connection(tmp_path)
    client.client.stderr_path = tmp_path / "prose.stderr.log"
    session = NativeValidationSession(ranked, tmp_path / "unpublished", profile_for(ranked), client)
    with capsys.disabled(), client:
        with pytest.raises(ValueError):
            run_validation_agent(session, Model(session))
    assert not (session.output_dir / "native_strategic_validation.json").exists()
    (tmp_path / "child.pid").unlink()
    mcp = tmp_path / "mcp.json"
    mcp.write_text(client.profile.model_dump_json())
    profile = tmp_path / "profile.json"
    profile.write_text(profile_for(ranked).model_dump_json())
    arguments = [
        "--ranking-run",
        str(ranked),
        "--validation-profile",
        str(profile),
        "--mcp-profile",
        str(mcp),
        "--output",
        str(tmp_path / "validated"),
    ]
    assert main(arguments) == 0
    result = json.loads(capsys.readouterr().out)
    assert len(result["attempts"]) == 8 and result["recommendation"] == "pending"
    (tmp_path / "child.pid").unlink()
    assert main(arguments) == 1
    assert not (tmp_path / "child.pid").exists()


def test_bad_operational_context_cannot_weaken_policy_or_drop_source_digests(ranked):
    profile = profile_for(ranked)
    candidate = json.loads((ranked / "preparation/inputs/candidate_strategies.json").read_bytes())[
        "strategies"
    ][0]
    payload = dict(
        run_id=profile.run_id,
        asset_id=profile.asset_id,
        cve_id="CVE-2021-44228",
        strategy_id=candidate["id"],
        ranking_decision_id="decision",
        ontology_individual="KG",
        action=candidate["action"],
        prerequisites=[],
        constraints=[],
        available_capabilities=[],
        prohibited_actions=[],
        constraint_mappings=[],
        evidence_digest="sha256:" + "a" * 64,
        candidates_digest="sha256:" + "b" * 64,
        policy_source="operator",
    )
    for field, value in [
        ("policy_digest", "sha256:" + "0" * 64),
        ("action", "unknown"),
        ("constraints", ["x", "x"]),
        ("available_capabilities", ["x", "x"]),
    ]:
        changed = copy.deepcopy(payload)
        changed[field] = value
        with pytest.raises(ValueError):
            OperationalContext.model_validate(changed)
