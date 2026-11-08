"""Checkpoint completo su processo esterno, CAMEL programmato e topologia dichiarata."""

import copy
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path

import pytest
from canonical_fixture import make_case
from test_camel_integration import ScriptedToolModel

from thesis_agents.canonical.contracts import PreparationRequest
from thesis_agents.canonical.preparation import canonical_artifact
from thesis_agents.canonical.session import PreparationSession

DEFAULT_REPO = Path("/Users/reucalion/Desktop/agent-based-cti-argumentation-pipeline")


@pytest.fixture
def canonical_case(tmp_path):
    source = (
        Path(os.environ.get("CANONICAL_GENERATOR_ROOT", DEFAULT_REPO)) / "app/semantic_preparation"
    )
    if not source.is_dir():
        pytest.skip("Install the pinned generator on external costa-thesis for process integration")
    repository = tmp_path / "repository"
    target = repository / "app/semantic_preparation"
    shutil.copytree(source, target, ignore=shutil.ignore_patterns("__pycache__"))
    subprocess.run(
        ["git", "init", "-b", "costa-thesis", str(repository)], check=True, capture_output=True
    )
    return make_case(tmp_path / "case", repository)


def test_external_generator_checkpoint_preserves_scope_and_native_ids(canonical_case, tmp_path):
    source, request, settings = canonical_case
    before = {p.name: p.read_bytes() for p in source.glob("*.json")}
    session = PreparationSession(source, tmp_path / "prepared", request, settings)
    result = session.prepare_argumentation()
    artifact = session.assert_complete()
    assert artifact.backend_weights == "not_computed" and artifact.deployment_verified is False
    graph = artifact.graphs[0]
    assert graph.topology == "bottalico-directed-ring-v1"
    assert len(graph.ranking_request.graph.nodes) == 5
    assert len(graph.ranking_request.graph.edges) == 8
    assert {n.id for n in graph.ranking_request.graph.nodes if n.type == "strategy"} == {
        b.ontology_individual for b in request.bindings
    }
    assert {b.strategy_id for b in request.bindings} != {
        b.ontology_individual for b in request.bindings
    }
    assert {edge.origin for edge in graph.edge_sources} == {
        "kg_remediation",
        "generator_comparison_ring",
    }
    assert all(edge.polarity == "deferred_to_shared_reasoner" for edge in graph.edge_sources)
    assert session.prepare_argumentation() == result
    assert len((session.output_dir / "preparation_events.jsonl").read_text().splitlines()) == 1
    assert before == {p.name: p.read_bytes() for p in source.glob("*.json")}
    assert not (session.output_dir / "ranking.json").exists()
    exported = session.output_dir / "ranking-requests" / f"{graph.cve_id}.json"
    assert json.loads(exported.read_text()) == graph.ranking_request.wire_payload()


def test_camel_role_and_clones_execute_only_two_authorized_tools(canonical_case, tmp_path):
    from thesis_agents.canonical.agent import build_preparation_agent, run_preparation_agent

    source, request, settings = canonical_case
    session = PreparationSession(source, tmp_path / "prepared", request, settings)

    class Model(ScriptedToolModel):
        def _run(self, messages, response_format=None, tools=None):
            if self.session._artifact is not None:
                return self._completion(content="Checkpoint published")
            tool = "get_context" if not self.tool_calls else "prepare_argumentation"
            assert {t["function"]["name"] for t in tools} == {tool}
            self.tool_calls.append(tool)
            return self._completion(
                tool_calls=[
                    {
                        "id": f"call-{len(self.tool_calls)}",
                        "type": "function",
                        "function": {"name": tool, "arguments": "{}"},
                    }
                ]
            )

    model = Model(session)
    agent = build_preparation_agent(session, model)
    assert set(agent.clone().clone().tool_dict) == {"get_context", "prepare_argumentation"}
    assert run_preparation_agent(session, model).graphs
    assert model.tool_calls == ["get_context", "prepare_argumentation"]


@pytest.mark.parametrize(
    "change", ["asset", "candidate", "source-digest", "observed-version", "run-id"]
)
def test_unrelated_inputs_rejected_before_output(canonical_case, tmp_path, change):
    source, request, settings = canonical_case
    payload = request.model_dump(mode="json")
    if change == "asset":
        payload["asset_id"] = "other"
    if change == "candidate":
        payload["bindings"][0]["strategy_id"] = "OTHER"
    if change == "source-digest":
        payload["input_digests"]["runtime_evidence"] = "0" * 64
    if change == "observed-version":
        payload["assessments"]["results"][0]["asset"]["version"] = "0.0"
    if change == "run-id":
        (source / "provenance.json").write_text(json.dumps({"run_id": "other"}))
    with pytest.raises(ValueError):
        PreparationSession(
            source, tmp_path / "prepared", PreparationRequest.model_validate(payload), settings
        )
    assert not (tmp_path / "prepared").exists()


@pytest.mark.parametrize(
    "change", ["branch", "code", "ontology", "kg-binding", "affected", "version"]
)
def test_generator_failure_never_publishes_checkpoint(canonical_case, tmp_path, change):
    source, request, settings = canonical_case
    if change == "branch":
        subprocess.run(
            ["git", "symbolic-ref", "HEAD", "refs/heads/main"], cwd=settings.repository, check=True
        )
    if change == "code":
        path = (
            settings.repository
            / "app/semantic_preparation/upstream/app/src/semantic_assets/argumentation_graph.py"
        )
        path.write_text(path.read_text() + "\n# changed\n")
    if change == "ontology":
        settings.source_ontology.write_text("Changed ontology")
    if change == "kg-binding":
        request.bindings[0].ontology_individual = "UnknownStrategy"
    if change == "affected":
        request.assessments.results[0].matches[0].affected_entries[
            0
        ].affected_iri = "UnknownAffected"
    if change == "version":
        request.assessments.results[0].matches[0].affected_entries[0].version_rules[
            0
        ].version_iri = "UnknownVersion"
    session = PreparationSession(source, tmp_path / "prepared", request, settings)
    with pytest.raises((ValueError, RuntimeError)):
        session.prepare_argumentation()
    assert not (session.output_dir / "canonical_preparation.json").exists()
    assert not (session.output_dir / "ranking.json").exists()
    assert (
        json.loads((session.output_dir / "preparation_events.jsonl").read_text())["status"]
        == "failed"
    )


@pytest.mark.parametrize(
    "file", ["aln_ontology.owl", "observed_assets.owl", "canonical_preparation.json"]
)
def test_published_artifact_mutation_is_detected(canonical_case, tmp_path, file):
    source, request, settings = canonical_case
    session = PreparationSession(source, tmp_path / "prepared", request, settings)
    session.prepare_argumentation()
    path = session.output_dir / file
    path.write_text(
        path.read_text().replace(
            '"backend_weights": "not_computed"', '"backend_weights": "invented"'
        )
        if file.endswith(".json")
        else "changed"
    )
    with pytest.raises(ValueError):
        session.assert_complete()


def test_wrong_generator_response_and_reordering(canonical_case, tmp_path):
    source, request, settings = canonical_case
    session = PreparationSession(source, tmp_path / "prepared", request, settings)
    expected = session.prepare_argumentation()
    payload = json.loads((session.output_dir / "generator-response.json").read_text())["payload"]
    reordered = copy.deepcopy(payload)
    graph = next(iter(reordered["graphs"].values()))
    graph["nodes"].reverse()
    graph["edges"].reverse()
    artifact, _ = canonical_artifact(request, settings, reordered)
    assert artifact.model_dump(mode="json", by_alias=True) == expected
    graph["edges"].pop()
    with pytest.raises(ValueError, match="topology"):
        canonical_artifact(request, settings, reordered)


def test_cli_uses_source_checkpoint(canonical_case, tmp_path, capsys):
    from thesis_agents.canonical.__main__ import main

    source, request, settings = canonical_case
    path = tmp_path / "request.json"
    path.write_text(request.model_dump_json())
    profile = tmp_path / "profile.json"
    profile.write_text(settings.model_dump_json())
    assert (
        main(
            [
                "--source-run",
                str(source),
                "--request",
                str(path),
                "--profile",
                str(profile),
                "--output",
                str(tmp_path / "prepared"),
            ]
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out)["contract"] == "canonical-preparation-v1"


def test_request_requires_confirmed_version_and_complete_digest_set(canonical_case):
    _, request, _ = canonical_case
    payload = request.model_dump(mode="json")
    payload["assessments"]["results"][0]["matches"][0]["affected_entries"][0]["version_rules"][0][
        "evaluated"
    ] = False
    with pytest.raises(ValueError):
        PreparationRequest.model_validate(payload)
    payload = request.model_dump(mode="json")
    payload["input_digests"].pop("runtime_evidence")
    with pytest.raises(ValueError):
        PreparationRequest.model_validate(payload)


def test_input_change_after_session_creation_blocks_invocation(canonical_case, tmp_path):
    source, request, settings = canonical_case
    session = PreparationSession(source, tmp_path / "prepared", request, settings)
    (source / "runtime_evidence.json").write_text("{}")
    with pytest.raises(ValueError, match="digest"):
        session.prepare_argumentation()
    assert not (session.output_dir / "generator-response.json").exists()


def test_multiple_cves_remain_separate_native_requests(canonical_case, tmp_path):
    source, request, settings = canonical_case
    old, new = "CVE-2021-44228", "CVE-2021-99999"
    report_path = source / "vulnerability_report.json"
    report = json.loads(report_path.read_text())
    extra = copy.deepcopy(report["vulnerabilities"][0])
    extra["cve_id"] = new
    report["vulnerabilities"].append(extra)
    report_path.write_text(json.dumps(report))
    candidate_path = source / "candidate_strategies.json"
    candidates = json.loads(candidate_path.read_text())
    for candidate in candidates["strategies"]:
        candidate["addressed_vulnerabilities"].append(new)
    candidate_path.write_text(json.dumps(candidates))
    payload = request.model_dump(mode="json")
    entry = payload["assessments"]["results"][0]["matches"][0]["affected_entries"][0]
    duplicate = json.loads(json.dumps(entry).replace(old, new))
    payload["assessments"]["results"][0]["matches"][0]["affected_entries"].append(duplicate)
    payload["bindings"] += json.loads(json.dumps(payload["bindings"]).replace(old, new))
    for name in ("vulnerability_report", "candidate_strategies"):
        payload["input_digests"][name] = hashlib.sha256(
            (source / f"{name}.json").read_bytes()
        ).hexdigest()
    lines = settings.source_ontology.read_text().splitlines()
    body = [line for line in lines if not line.startswith(("Prefix", "Ontology")) and line != ")"]
    settings.source_ontology.write_text(
        "\n".join(lines[:-1] + [line.replace(old, new) for line in body] + [")"]) + "\n"
    )
    settings.source_ontology_sha256 = hashlib.sha256(
        settings.source_ontology.read_bytes()
    ).hexdigest()
    session = PreparationSession(
        source, tmp_path / "prepared", PreparationRequest.model_validate(payload), settings
    )
    session.prepare_argumentation()
    assert [g.cve_id for g in session.assert_complete().graphs] == [old, new]


def test_timeout_kills_generator_and_preserves_failure(canonical_case, tmp_path):
    source, request, settings = canonical_case
    package = settings.repository / "app/semantic_preparation"
    pid_path = tmp_path / "generator.pid"
    runner = package / "runner.py"
    runner.write_text(
        "import os,time\nfrom pathlib import Path\n"
        + f"Path({str(pid_path)!r}).write_text(str(os.getpid()))\ntime.sleep(20)\n"
    )
    manifest_path = package / "installation-manifest.json"
    manifest = json.loads(manifest_path.read_text())
    manifest["files"]["runner.py"] = hashlib.sha256(runner.read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(manifest))
    settings.generator_manifest_sha256 = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    settings.timeout_seconds = 0.3
    session = PreparationSession(source, tmp_path / "prepared", request, settings)
    with pytest.raises(RuntimeError, match="timed out"):
        session.prepare_argumentation()
    with pytest.raises(ProcessLookupError):
        os.kill(int(pid_path.read_text()), 0)
    assert not (session.output_dir / "canonical_preparation.json").exists()


def test_source_change_during_generation_is_not_published(canonical_case, tmp_path, monkeypatch):
    from thesis_agents.canonical.preparation import ExternalPreparationTool

    source, request, settings = canonical_case
    original = ExternalPreparationTool.prepare

    def changed(self, request, output):
        result = original(self, request, output)
        (source / "runtime_evidence.json").write_text("{}")
        return result

    monkeypatch.setattr(ExternalPreparationTool, "prepare", changed)
    session = PreparationSession(source, tmp_path / "prepared", request, settings)
    with pytest.raises(ValueError, match="digest"):
        session.prepare_argumentation()
    assert not (session.output_dir / "canonical_preparation.json").exists()
    assert (
        json.loads((session.output_dir / "preparation_events.jsonl").read_text())["status"]
        == "failed"
    )


def test_agent_prose_cannot_publish_checkpoint(canonical_case, tmp_path):
    from thesis_agents.canonical.agent import run_preparation_agent

    source, request, settings = canonical_case
    session = PreparationSession(source, tmp_path / "prepared", request, settings)

    class Model(ScriptedToolModel):
        def _run(self, messages, response_format=None, tools=None):
            return self._completion(content="Everything completed successfully")

    with pytest.raises(ValueError, match="unpublished"):
        run_preparation_agent(session, Model(session))
    assert not (session.output_dir / "canonical_preparation.json").exists()


def test_request_contract_without_external_installation():
    with pytest.raises(ValueError, match="confirmed evaluated"):
        from thesis_agents.canonical.contracts import EvaluatedVersion

        EvaluatedVersion(
            evaluated=False,
            matched_asset_version=True,
            vulnerability_status="vulnerable",
            version_iri="Version_1",
        )


def test_process_settings_reject_relative_paths_without_external_installation():
    from thesis_agents.canonical.preparation import PreparationSettings

    with pytest.raises(ValueError, match="absolute"):
        PreparationSettings(
            repository=Path("relative"),
            python=Path("/usr/bin/python3"),
            source_ontology=Path("/tmp/source.owl"),
            source_ontology_sha256="0" * 64,
            generator_manifest_sha256="0" * 64,
            knowledge_snapshot_id="fixture",
        )


def test_canonical_graph_contract_rejects_incomplete_topology_without_installation():
    from thesis_agents.canonical.contracts import CanonicalGraph

    native = {
        "cve_id": "CVE-2021-44228",
        "candidates": [{"id": "S1", "name": "S1"}],
        "graph": {
            "nodes": [
                {"id": "CVE-2021-44228", "type": "vulnerability"},
                {"id": "S1", "type": "strategy"},
            ],
            "edges": [],
        },
    }
    with pytest.raises(ValueError, match="topology"):
        CanonicalGraph(cve_id=native["cve_id"], ranking_request=native, edge_sources=[])


def test_canonical_graph_contract_rejects_claimed_attack_without_installation():
    from thesis_agents.canonical.contracts import CanonicalEdge

    with pytest.raises(ValueError):
        CanonicalEdge(
            **{
                "from": "CVE-2021-44228",
                "to": "S1",
                "origin": "kg_remediation",
                "polarity": "attack",
            }
        )
