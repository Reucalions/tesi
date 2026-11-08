"""Strategic nativo: checkpoint reale, stdio effettivo, SaaS e inferenza simulati."""

import copy
import json
from concurrent.futures import ThreadPoolExecutor

import pytest
from canonical_fixture import make_case
from test_camel_integration import ScriptedToolModel
from test_mcp_stdio import assert_child_stopped, stdio_settings

from thesis_agents.canonical.contracts import PreparationRequest
from thesis_agents.canonical.preparation import (
    ExternalPreparationTool,
    bytes_digest,
    canonical_artifact,
)
from thesis_agents.canonical.session import PreparationSession
from thesis_agents.mcp.client import MCPError
from thesis_agents.mcp.shared_client import SharedMCPProfile, SharedServicesClient
from thesis_agents.strategic.agent import (
    NATIVE_STRATEGIC_CONTRACT,
    build_native_strategic_agent,
    run_native_strategic_agent,
)
from thesis_agents.strategic.contracts import NativeRankingSettings, NativeStrategicRanking
from thesis_agents.strategic.session import NativeStrategicSession


@pytest.fixture
def prepared(tmp_path, monkeypatch, request):
    candidate_count = getattr(request, "param", 4)
    # Only generation is stubbed here: external process integration has its own tests.
    repository = tmp_path / "repository"
    package = repository / "app/semantic_preparation"
    package.mkdir(parents=True)
    (package / "installation-manifest.json").write_text('{"fixture":true}')
    source, request, profile = make_case(tmp_path / "case", repository)
    old, new = "CVE-2021-44228", "CVE-2021-99999"
    report_path = source / "vulnerability_report.json"
    report = json.loads(report_path.read_bytes())
    extra = copy.deepcopy(report["vulnerabilities"][0])
    extra["cve_id"] = new
    report["vulnerabilities"].append(extra)
    report_path.write_text(json.dumps(report))
    candidate_path = source / "candidate_strategies.json"
    candidates = json.loads(candidate_path.read_bytes())
    candidates["strategies"] = candidates["strategies"][:candidate_count]
    for candidate in candidates["strategies"]:
        candidate["addressed_vulnerabilities"].append(new)
    candidate_path.write_text(json.dumps(candidates))
    payload = request.model_dump(mode="json")
    entries = payload["assessments"]["results"][0]["matches"][0]["affected_entries"]
    entries.append(json.loads(json.dumps(entries[0]).replace(old, new)))
    payload["bindings"] += json.loads(json.dumps(payload["bindings"]).replace(old, new))
    selected_ids = {candidate["id"] for candidate in candidates["strategies"]}
    payload["bindings"] = [b for b in payload["bindings"] if b["strategy_id"] in selected_ids]
    for name in ("vulnerability_report", "candidate_strategies"):
        payload["input_digests"][name] = bytes_digest((source / f"{name}.json").read_bytes())
    request = PreparationRequest.model_validate(payload)
    raw = {
        "graphs": {},
        "observed_assets_owl": "Synthetic observed assets\n",
        "aln_ontology": "Synthetic ALN\n",
        "source_ontology_sha256": profile.source_ontology_sha256,
        "generator_manifest_sha256": profile.generator_manifest_sha256,
    }
    for cve in (old, new):
        names = sorted(b.ontology_individual for b in request.bindings if b.cve_id == cve)
        raw["graphs"][cve] = {
            "nodes": [{"id": cve, "type": "vulnerability"}]
            + [{"id": name, "type": "strategy"} for name in names],
            "edges": [{"from": cve, "to": name} for name in names]
            + (
                [{"from": a, "to": b} for a, b in zip(names, names[1:] + names[:1], strict=True)]
                if len(names) > 1
                else []
            ),
        }
    monkeypatch.setattr(
        ExternalPreparationTool,
        "prepare",
        lambda self, request, output: canonical_artifact(request, profile, raw),
    )
    session = PreparationSession(source, tmp_path / "prepared", request, profile)
    session.prepare_argumentation()
    return session.output_dir


def settings():
    return NativeRankingSettings(
        tenant_id="fixture",
        knowledge_snapshot_id="urn:inspection:canonical-fixture",
        knowledge_snapshot_digest="sha256:" + "b" * 64,
        ontology_digest="sha256:" + "a" * 64,
    )


def connection(tmp_path, fault="none"):
    return SharedServicesClient(
        SharedMCPProfile(connection=stdio_settings(tmp_path, kind="shared", fault=fault))
    )


def complete(session):
    session.get_context()
    while operation := session.next_operation():
        operation = dict(operation)
        getattr(session, operation.pop("tool"))(**operation)
    return session.assert_complete()


def test_multiple_cves_native_scores_exact_ids_and_readbacks(prepared, tmp_path):
    original = {str(p): p.read_bytes() for p in prepared.rglob("*") if p.is_file()}
    client = connection(tmp_path)
    session = NativeStrategicSession(prepared, tmp_path / "strategic", settings(), client)
    with client:
        result = complete(session)
        assert session.publish_native_ranking() == result.model_dump(mode="json", by_alias=True)
    assert [r.cve_id for r in result.results] == ["CVE-2021-44228", "CVE-2021-99999"]
    assert len({r.ranking.decision_id for r in result.results}) == 2
    for row in result.results:
        assert [r.score for r in row.ranking.ranked_strategies] == [10, 5, 10 / 3, 2.5]
        assert {b.strategy_id for b in row.bindings} != {
            b.ontology_individual for b in row.bindings
        }
        assert row.decision_readback.ranked_strategies == row.ranking.ranked_strategies
        assert row.provenance_readback.slsa_assurance == row.ranking.slsa_assurance
    assert result.backend_kind == "mock" and result.deployment_verified is False
    assert result.recommendation == result.semantic_validation == "pending"
    assert not (session.output_dir / "final_decision.json").exists()
    assert original == {str(p): p.read_bytes() for p in prepared.rglob("*") if p.is_file()}
    assert_child_stopped(tmp_path / "child.pid")


@pytest.mark.parametrize("fault", ["tied-scores", "negative-scores"])
def test_ties_follow_kg_ids_and_negative_scores_are_preserved(prepared, tmp_path, fault):
    client = connection(tmp_path, fault)
    session = NativeStrategicSession(prepared, tmp_path / "strategic", settings(), client)
    with client:
        artifact = complete(session)
    for result in artifact.results:
        rows = result.ranking.ranked_strategies
        assert [row.id for row in rows] == sorted(row.id for row in rows)
        expected = [7.5] * 4 if fault == "tied-scores" else [-1, -2, -3, -4]
        assert [row.score for row in rows] == expected


@pytest.mark.parametrize("prepared", [1], indirect=True)
def test_single_candidate_still_calls_remote_and_keeps_zero_score(prepared, tmp_path):
    client = connection(tmp_path, "zero-score")
    session = NativeStrategicSession(prepared, tmp_path / "strategic", settings(), client)
    with client:
        artifact = complete(session)
    for result in artifact.results:
        assert len(result.ranking.ranked_strategies) == 1
        assert result.ranking.ranked_strategies[0].score == 0
    events = [
        json.loads(line)
        for line in (session.output_dir / "strategic_events.jsonl").read_text().splitlines()
    ]
    assert [event["tool"] for event in events].count("rank_remediations") == 2


@pytest.mark.parametrize("field", ["tenant_id", "ontology_digest", "knowledge_snapshot_digest"])
def test_strategic_pins_fail_without_publishing_or_retry(prepared, tmp_path, field):
    profile = settings()
    setattr(profile, field, "other" if field == "tenant_id" else "sha256:" + "0" * 64)
    client = connection(tmp_path)
    session = NativeStrategicSession(prepared, tmp_path / "strategic", profile, client)
    with client:
        with pytest.raises(ValueError, match="pins"):
            complete(session)
        assert session._failed and session.next_operation() is None
        with pytest.raises(ValueError, match="out of phase"):
            session.rank_remediations("CVE-2021-44228")
    assert not (session.output_dir / "native_strategic_ranking.json").exists()
    assert (session.output_dir / "native/CVE-2021-44228/rank_remediations.json").exists()
    events = (session.output_dir / "strategic_events.jsonl").read_text().splitlines()
    assert len(events) == 1 and json.loads(events[0])["status"] == "failed"


@pytest.mark.parametrize(
    "fault",
    [
        "wrong-cve",
        "wrong-candidate",
        "wrong-digest",
        "wrong-snapshot",
        "bad-score",
        "read-status",
        "read-snapshot",
        "read-assurance",
        "duplicate-decision",
        "tool-error",
        "disconnect",
        "timeout",
    ],
)
def test_remote_error_is_failure_not_abstention(prepared, tmp_path, fault):
    client = connection(tmp_path, fault)
    if fault == "timeout":
        client.profile = client.profile.model_copy(
            update={
                "connection": client.profile.connection.model_copy(update={"timeout_seconds": 1})
            }
        )
        client.client.settings = client.profile.connection
    session = NativeStrategicSession(prepared, tmp_path / "strategic", settings(), client)
    with client:
        with pytest.raises(MCPError):
            complete(session)
    assert session._failed
    assert not (session.output_dir / "native_strategic_ranking.json").exists()
    assert not (session.output_dir / "final_decision.json").exists()
    assert_child_stopped(tmp_path / "child.pid")


@pytest.mark.parametrize(
    "name",
    [
        "inputs/runtime_evidence.json",
        "request.json",
        "profile.json",
        "aln_ontology.owl",
        "observed_assets.owl",
        "canonical_preparation.json",
        "ranking-requests/CVE-2021-44228.json",
    ],
)
def test_tampered_preparation_rejected_before_mcp_or_output(prepared, tmp_path, name):
    (prepared / name).write_text("{}")
    with pytest.raises(ValueError):
        NativeStrategicSession(prepared, tmp_path / "strategic", settings(), connection(tmp_path))
    assert not (tmp_path / "strategic").exists()
    assert not (tmp_path / "child.pid").exists()


def test_request_binding_change_cannot_relabel_mas_ids(prepared, tmp_path):
    path = prepared / "canonical_preparation.json"
    payload = json.loads(path.read_bytes())
    # Permute IDs while retaining exact native candidate coverage (valid contract alone).
    a, b = payload["bindings"][:2]
    a["strategy_id"], b["strategy_id"] = b["strategy_id"], a["strategy_id"]
    path.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match="request/profile"):
        NativeStrategicSession(prepared, tmp_path / "strategic", settings(), connection(tmp_path))


@pytest.mark.parametrize("change", ["source", "copy", "profile", "response", "memory"])
def test_changed_inputs_or_responses_block_next_remote_call(prepared, tmp_path, change):
    client = connection(tmp_path)
    session = NativeStrategicSession(prepared, tmp_path / "strategic", settings(), client)
    with client:
        cve = "CVE-2021-44228"
        session.rank_remediations(cve)
        if change == "source":
            (prepared / "aln_ontology.owl").write_text("changed")
        elif change == "copy":
            (session.output_dir / "preparation/inputs/runtime_evidence.json").write_text("{}")
        elif change == "profile":
            (session.output_dir / "ranking-profile.json").write_text("{}")
        elif change == "response":
            (session.output_dir / f"native/{cve}/rank_remediations.json").write_text("{}")
        else:
            session.preparation.bindings[0].strategy_id = "INVENTED"
        with pytest.raises(ValueError):
            session.get_decision(cve)
        assert not (session.output_dir / f"native/{cve}/get_decision.json").exists()


def test_phase_scope_and_incomplete_publication(prepared, tmp_path):
    client = connection(tmp_path)
    session = NativeStrategicSession(prepared, tmp_path / "strategic", settings(), client)
    with client:
        for tool, cve in [
            ("get_decision", "CVE-2021-44228"),
            ("rank_remediations", "CVE-2021-99999"),
            ("rank_remediations", "CVE-2025-12345"),
        ]:
            with pytest.raises(ValueError, match="out of phase"):
                getattr(session, tool)(cve)
        with pytest.raises(ValueError, match="incomplete"):
            session.publish_native_ranking()
        result = complete(session)
    path = session.output_dir / "native_strategic_ranking.json"
    payload = result.model_dump(mode="json", by_alias=True)
    payload["results"].pop()
    path.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match="changed"):
        session.assert_complete()


def test_duplicate_parallel_tool_calls_cannot_rank_twice(prepared, tmp_path):
    events = []
    client = connection(tmp_path)
    client.client.audit = events.append
    session = NativeStrategicSession(prepared, tmp_path / "strategic", settings(), client)
    with client, ThreadPoolExecutor(max_workers=2) as pool:
        futures = [pool.submit(session.rank_remediations, "CVE-2021-44228") for _ in range(2)]
        assert sum(future.exception() is None for future in futures) == 1
        assert sum(isinstance(future.exception(), ValueError) for future in futures) == 1
        assert len([e for e in events if e.get("tool") == "rank_remediations"]) == 1


@pytest.mark.parametrize("field", ["semantic_validation", "recommendation", "deployment_verified"])
def test_checkpoint_cannot_claim_semantic_finalization(prepared, tmp_path, field):
    client = connection(tmp_path)
    session = NativeStrategicSession(prepared, tmp_path / "strategic", settings(), client)
    with client:
        payload = complete(session).model_dump(mode="json", by_alias=True)
    payload[field] = True if field == "deployment_verified" else "accepted"
    with pytest.raises(ValueError):
        NativeStrategicRanking.model_validate(payload)


def test_camel_native_role_and_clones_execute_all_individual_tools(prepared, tmp_path):
    client = connection(tmp_path)
    session = NativeStrategicSession(prepared, tmp_path / "strategic", settings(), client)

    class Model(ScriptedToolModel):
        def _run(self, messages, response_format=None, tools=None):
            names = {t["function"]["name"] for t in tools or []}
            if not names:
                return self._completion(content="Published native checkpoint")
            tool = names.pop()
            args = (
                {}
                if tool == "get_context"
                else {k: v for k, v in self.session.next_operation().items() if k != "tool"}
            )
            self.tool_calls.append((tool, args))
            return self._completion(
                tool_calls=[
                    {
                        "id": f"call-{len(self.tool_calls)}",
                        "type": "function",
                        "function": {"name": tool, "arguments": json.dumps(args)},
                    }
                ]
            )

    model = Model(session)
    agent = build_native_strategic_agent(session, model)
    clone = agent.clone().clone()
    assert clone.tool_policy.next_tool() == "get_context"
    assert set(clone.tool_dict) == set(NATIVE_STRATEGIC_CONTRACT.module.TOOLS)
    with client:
        result = run_native_strategic_agent(session, model)
    assert len(result.results) == 2
    assert [name for name, _ in model.tool_calls] == [
        "get_context",
        "rank_remediations",
        "get_decision",
        "get_provenance",
        "rank_remediations",
        "get_decision",
        "get_provenance",
        "publish_native_ranking",
    ]
    assert clone.tool_policy.next_tool() == "get_context"
    assert_child_stopped(tmp_path / "child.pid")


def test_camel_prose_cannot_publish_ranking(prepared, tmp_path):
    class TextModel(ScriptedToolModel):
        def _run(self, messages, response_format=None, tools=None):
            return self._completion(content="All rankings published")

    client = connection(tmp_path)
    session = NativeStrategicSession(prepared, tmp_path / "strategic", settings(), client)
    with client:
        with pytest.raises(ValueError, match="unpublished"):
            run_native_strategic_agent(session, TextModel(session))
    assert not (session.output_dir / "native_strategic_ranking.json").exists()


def test_cli_native_checkpoint_and_fail_before_startup(prepared, tmp_path, capsys):
    from thesis_agents.strategic.__main__ import main

    mcp_profile, ranking_profile = tmp_path / "mcp.json", tmp_path / "ranking.json"
    mcp_profile.write_text(connection(tmp_path).profile.model_dump_json())
    ranking_profile.write_text(settings().model_dump_json())
    arguments = [
        "--prepared",
        str(prepared),
        "--mcp-profile",
        str(mcp_profile),
        "--ranking-profile",
        str(ranking_profile),
        "--output",
        str(tmp_path / "strategic"),
    ]
    assert main(arguments) == 0
    payload = json.loads(capsys.readouterr().out)
    assert len(payload["results"]) == 2 and payload["recommendation"] == "pending"
    assert_child_stopped(tmp_path / "child.pid")
    (tmp_path / "child.pid").unlink()
    assert main(arguments) == 1  # Existing output must never be overwritten.
    assert not (tmp_path / "child.pid").exists()
    capsys.readouterr()
