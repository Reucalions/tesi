"""Selection from actual MCP stdio validations; inference/services remain synthetic."""

import copy
import json
from concurrent.futures import ThreadPoolExecutor

import pytest
import test_operational_validation as validation_tests
from test_camel_integration import ScriptedToolModel
from test_native_strategic import connection
from test_operational_validation import profile_for, validate_all

from thesis_agents.mcp.operational_contracts import ACTION_REQUIREMENTS
from thesis_agents.strategic.selection import main
from thesis_agents.strategic.selection_agent import build_selection_agent, run_selection_agent
from thesis_agents.strategic.selection_contracts import NativeStrategicRecommendation
from thesis_agents.strategic.selection_session import (
    NativeSelectionSession,
    load_validation_checkpoint,
)
from thesis_agents.strategic.validation_session import NativeValidationSession

canonical_prepared = validation_tests.canonical_prepared
ranked = validation_tests.ranked


def validated_case(ranked, tmp_path, scenario="accepted"):
    profile = profile_for(ranked)
    fault = "none"
    if scenario == "alternative":
        profile.prohibited_actions = ["upgrade"]
    elif scenario == "semantic-alternative":
        fault = "semantic-first-rejected"
    elif scenario == "independent-cves":
        fault = "semantic-one-cve-rejected"
    elif scenario == "missing":
        profile.available_capabilities = []
    elif scenario == "review":
        profile.constraint_mappings = []
    elif scenario == "rejected":
        profile.prohibited_actions = list(ACTION_REQUIREMENTS)
    elif scenario == "mixed":
        profile.available_capabilities.remove("maintenance_window")
        profile.constraint_mappings = [
            m for m in profile.constraint_mappings if m.strategy_id != "S_ISOLATE"
        ]
        profile.prohibited_actions = ["block_deployment", "monitor"]
    client = connection(tmp_path, fault)
    session = NativeValidationSession(ranked, tmp_path / "validated", profile, client)
    with client:
        artifact = validate_all(session)
    return session.output_dir, artifact


@pytest.mark.parametrize(
    "scenario,selected,outcome",
    [
        ("accepted", "S_UPGRADE", "recommended"),
        ("alternative", "S_ISOLATE", "recommended"),
        ("semantic-alternative", "S_ISOLATE", "recommended"),
        ("missing", None, "requires_prerequisites"),
        ("review", None, "requires_review"),
        ("rejected", None, "no_valid_strategy"),
        ("mixed", None, "requires_review"),
    ],
)
def test_first_effective_acceptance_per_cve_preserves_every_native_outcome(
    ranked, tmp_path, scenario, selected, outcome
):
    directory, validation = validated_case(ranked, tmp_path, scenario)
    original = {str(p): p.read_bytes() for p in directory.rglob("*") if p.is_file()}
    session = NativeSelectionSession(directory, tmp_path / "selection")
    session.get_context()
    publication = session.publish_native_recommendation()
    artifact = session.assert_complete()
    assert publication == session.publish_native_recommendation()
    assert len(artifact.results) == 2
    for result in artifact.results:
        assert result.selected_strategy_id == selected and result.outcome == outcome
        assert [r.ranking.score for r in result.candidates] == [10, 5, 10 / 3, 2.5]
        assert [r.validation for r in result.candidates] == [
            a for a in validation.attempts if a.cve_id == result.cve_id
        ]
        if selected:
            choice = next(r for r in result.candidates if r.disposition == "selected")
            assert choice.validation.strategy_id == selected
            assert choice.validation.response.effective_status == "accepted"
            assert choice.validation.request.countermeasure_iri.endswith(choice.ranking.id)
            assert choice.ranking.id != selected
        else:
            assert all(r.disposition == "not_acceptable" for r in result.candidates)
    assert artifact.shared_finalization == "pending" and artifact.status == "dry_run_completed"
    assert artifact.deployment_verified is False and artifact.action_execution == "not_performed"
    assert artifact.provenance_scope == "local_artifact_lineage"
    assert original == {str(p): p.read_bytes() for p in directory.rglob("*") if p.is_file()}


@pytest.mark.parametrize(
    "fault,scores",
    [
        ("tied-scores", [7.5] * 4),
        ("negative-scores", [-1, -2, -3, -4]),
    ],
)
def test_selection_preserves_native_ties_and_unbounded_negative_scores(
    canonical_prepared, tmp_path, fault, scores
):
    from test_native_strategic import complete, settings

    from thesis_agents.strategic.session import NativeStrategicSession

    client = connection(tmp_path, fault)
    ranking = NativeStrategicSession(canonical_prepared, tmp_path / "rank", settings(), client)
    with client:
        complete(ranking)
    directory, _ = validated_case(ranking.output_dir, tmp_path)
    selection = NativeSelectionSession(directory, tmp_path / "selection")
    selection.publish_native_recommendation()
    for result in selection.assert_complete().results:
        assert result.selected_strategy_id == "S_UPGRADE"
        assert [r.ranking.score for r in result.candidates] == scores


@pytest.fixture
def validated(ranked, tmp_path):
    return validated_case(ranked, tmp_path)[0]


def test_each_cve_has_its_own_decision_without_promoting_another_cve_winner(ranked, tmp_path):
    directory, _ = validated_case(ranked, tmp_path, "independent-cves")
    session = NativeSelectionSession(directory, tmp_path / "selection")
    session.publish_native_recommendation()
    first, second = session.assert_complete().results
    assert first.cve_id == "CVE-2021-44228" and first.outcome == "no_valid_strategy"
    assert first.selected_strategy_id is None
    assert second.cve_id == "CVE-2021-99999" and second.outcome == "recommended"
    assert second.selected_strategy_id == "S_UPGRADE"
    assert first.ranking_decision_id != second.ranking_decision_id


@pytest.mark.parametrize(
    "change",
    [
        "missing-attempt",
        "order",
        "run",
        "profile",
        "request",
        "response",
        "iri",
        "ranking",
        "backend",
        "unfinished",
    ],
)
def test_bad_or_incomplete_checkpoint_fails_before_selection_output(validated, tmp_path, change):
    path = validated / "native_strategic_validation.json"
    data = json.loads(path.read_bytes())
    if change == "missing-attempt":
        data["attempts"].pop()
    elif change == "order":
        data["attempts"].reverse()
    elif change == "run":
        data["run_id"] = "another-run"
    elif change == "profile":
        data["profile_sha256"] = "0" * 64
    elif change == "request":
        next((validated / "attempts").rglob("*.request.json")).write_text("{}")
    elif change == "response":
        next(
            p
            for p in (validated / "attempts").rglob("*.json")
            if not p.name.endswith(".request.json")
        ).write_text("{}")
    elif change == "iri":
        data["attempts"][0]["request"]["countermeasure_iri"] = "urn:other:strategy"
    elif change == "ranking":
        (validated / "ranking-input/native_strategic_ranking.json").write_text("{}")
    elif change == "backend":
        profile_path = validated / "mcp-profile.json"
        profile = json.loads(profile_path.read_bytes())
        profile["connection"]["expected_kind"] = "real"
        profile_path.write_text(json.dumps(profile))
    if change == "unfinished":
        path.unlink()
    else:
        path.write_text(json.dumps(data))
    with pytest.raises((ValueError, OSError)):
        NativeSelectionSession(validated, tmp_path / "selection")
    assert not (tmp_path / "selection").exists()


@pytest.mark.parametrize("change", ["source", "copy", "memory", "expected"])
def test_mutation_between_context_and_publication_blocks_selection(validated, tmp_path, change):
    session = NativeSelectionSession(validated, tmp_path / "selection")
    session.get_context()
    if change in ("source", "copy"):
        root = validated if change == "source" else session.output_dir / "validation-input"
        (root / "validation-profile.json").write_text("{}")
    elif change == "memory":
        session._checkpoint[0].attempts.pop()
    else:
        session._expected.results[0].selected_strategy_id = "S_ISOLATE"
    with pytest.raises((ValueError, OSError)):
        session.publish_native_recommendation()
    assert session._failed and session.next_operation() is None
    assert not (session.output_dir / "native_strategic_recommendation.json").exists()


def test_changed_output_or_later_accepted_candidate_cannot_override_selection(validated, tmp_path):
    session = NativeSelectionSession(validated, tmp_path / "selection")
    session.publish_native_recommendation()
    data = session.assert_complete().model_dump(mode="json", by_alias=True)
    forged = copy.deepcopy(data)
    forged["results"][0]["selected_strategy_id"] = "S_ISOLATE"
    with pytest.raises(ValueError):
        NativeStrategicRecommendation.model_validate(forged)
    path = session.output_dir / "native_strategic_recommendation.json"
    data["results"].pop()
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError):
        session.assert_complete()


def test_duplicate_parallel_publication_and_existing_directory_are_safe(validated, tmp_path):
    session = NativeSelectionSession(validated, tmp_path / "selection")
    with pytest.raises(FileExistsError):
        NativeSelectionSession(validated, tmp_path / "selection")
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: session.publish_native_recommendation(), range(2)))
    assert results[0] == results[1]
    session.assert_complete()


def test_camel_clones_publish_and_prose_cannot_replace_tools(validated, tmp_path):
    session = NativeSelectionSession(validated, tmp_path / "selection")

    class Model(ScriptedToolModel):
        def _run(self, messages, response_format=None, tools=None):
            names = {t["function"]["name"] for t in tools or []}
            if not names:
                return self._completion(content="Published")
            name = names.pop()
            self.tool_calls.append(name)
            return self._completion(
                tool_calls=[
                    {
                        "id": f"call-{len(self.tool_calls)}",
                        "type": "function",
                        "function": {"name": name, "arguments": "{}"},
                    }
                ]
            )

    model = Model(session)
    clone = build_selection_agent(session, model).clone().clone()
    assert clone.tool_policy.next_tool() == "get_context"
    clone.step("Publish native recommendation")
    session.assert_complete()
    assert model.tool_calls == ["get_context", "publish_native_recommendation"]

    class Prose(Model):
        def _run(self, *args, **kwargs):
            return self._completion(content="I recommend S_UPGRADE")

    other = NativeSelectionSession(validated, tmp_path / "unpublished")
    with pytest.raises(ValueError):
        run_selection_agent(other, Prose(other))
    assert not (other.output_dir / "native_strategic_recommendation.json").exists()


def test_cli_offline_has_no_dependency_on_original_generator_or_remote_service(
    validated, tmp_path, capsys
):
    # The archived profiles intentionally reference inaccessible fixture paths.
    assert load_validation_checkpoint(validated)[0].attempts
    args = ["--validation-run", str(validated), "--output", str(tmp_path / "selection")]
    assert main(args) == 0
    result = json.loads(capsys.readouterr().out)
    assert len(result["results"]) == 2 and result["results"][0]["outcome"] == "recommended"
    assert main(args) == 1
