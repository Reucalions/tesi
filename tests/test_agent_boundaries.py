"""Verifiche dei ruoli SDK e del confine comune verso backend sostituibili."""

import pytest
from pydantic import ValidationError
from test_camel_integration import ScriptedToolModel

from thesis_agents.agents.contracts import AGENT_CONTRACTS
from thesis_agents.fixtures import fixture_candidates, fixture_evidence
from thesis_agents.orchestration.artifacts import ARTIFACT_SCHEMAS, ArtifactSession, json_payload
from thesis_agents.orchestration.workforce import build_workforce
from thesis_agents.schemas import RankingResult
from thesis_agents.tools.ranking_mock import MockRankingTool
from thesis_agents.tools.semantic_mock import MockSemanticTool
from thesis_agents.tools.vulnerability_mock import MockVulnerabilityTool


def test_sdk_workers_enforce_declared_artifacts_and_tool_ownership(session):
    workforce = build_workforce(session, lambda: ScriptedToolModel(session))
    outputs = []
    for contract, worker in zip(AGENT_CONTRACTS, workforce._children, strict=True):
        outputs.extend(contract.outputs)
        assert worker.structured_handler.inputs == contract.inputs
        assert worker.structured_handler.outputs == contract.outputs
        # Controlla anche i cloni usati dal pool CAMEL, non solo la configurazione.
        registered = set(worker.worker.clone().clone().tool_dict)
        expected = set(contract.module.TOOLS) - {
            "collect_runtime_evidence",
            "collect_countermeasure_context",
            "prepare_package_verification",
        }
        assert registered == expected
    assert len(outputs) == len(set(outputs))
    assert set(outputs) == set(ARTIFACT_SCHEMAS)
    assert set(session.get_context()["artifacts"]) == {"input"}


@pytest.mark.parametrize(
    "changes",
    [
        {"package": "unrelated-package"},
        {"observed_version": "unrelated-version"},
        {"evidence_ids": ["UNRELATED_EVIDENCE"]},
        {"evidence_ids": ["E1", "UNRELATED_EVIDENCE"]},
    ],
)
def test_unrelated_lookup_is_rejected_before_caching_and_can_be_retried(session, changes):
    class Lookup:
        faulty = True
        calls = 0

        def lookup_vulnerabilities(self, software):
            self.calls += 1
            result = MockVulnerabilityTool().lookup_vulnerabilities(software)
            if self.faulty:
                result.vulnerabilities[0] = result.vulnerabilities[0].model_copy(update=changes)
            return result

    backend = Lookup()
    session.vulnerability_tool = backend
    session.publish_runtime_evidence(json_payload(fixture_evidence(session)))
    before = (session.output_dir / "runtime_evidence.json").read_bytes()
    with pytest.raises(ValueError, match="observed software evidence"):
        session.lookup_vulnerabilities()
    assert session._lookup is None
    assert not (session.output_dir / "vulnerability_report.json").exists()
    # Il tentativo fallito non diventa un risultato vuoto o una cache permanente.
    backend.faulty = False
    report = session.lookup_vulnerabilities()
    assert session.publish_vulnerability_report(json_payload(report)) == report
    assert backend.calls == 2
    assert (session.output_dir / "runtime_evidence.json").read_bytes() == before


def test_backend_cannot_change_the_lookup_observation(session):
    class MutatingLookup:
        def lookup_vulnerabilities(self, software):
            software.evidence_id = "CHANGED_BY_BACKEND"
            return MockVulnerabilityTool().lookup_vulnerabilities(software)

    session.vulnerability_tool = MutatingLookup()
    session.publish_runtime_evidence(json_payload(fixture_evidence(session)))
    with pytest.raises(ValueError, match="observed software evidence"):
        session.lookup_vulnerabilities()
    assert session.get_context()["artifacts"]["runtime_evidence"]["software"][0][
        "evidence_id"
    ] == "E1"
    assert session._lookup is None


def test_lookup_revalidates_nested_backend_models(session):
    class InvalidLookup:
        def lookup_vulnerabilities(self, software):
            result = MockVulnerabilityTool().lookup_vulnerabilities(software)
            result.vulnerabilities[0] = result.vulnerabilities[0].model_copy(update={"cvss": 99})
            return result

    session.vulnerability_tool = InvalidLookup()
    session.publish_runtime_evidence(json_payload(fixture_evidence(session)))
    with pytest.raises(ValidationError, match="cvss"):
        session.lookup_vulnerabilities()
    assert session._lookup is None


@pytest.mark.parametrize("stage", ["lookup", "ranking", "semantic"])
def test_backend_timeout_preserves_artifacts_without_publishing_a_decision(session, stage):
    class Unavailable:
        def lookup_vulnerabilities(self, software):
            raise TimeoutError("lookup unavailable")

        def rank_graph(self, graph):
            raise TimeoutError("ranking unavailable")

        def validate_countermeasure(self, strategy, context):
            raise TimeoutError("semantic unavailable")

    session.publish_runtime_evidence(json_payload(fixture_evidence(session)))
    if stage == "lookup":
        session.vulnerability_tool = Unavailable()
        call = session.lookup_vulnerabilities
    else:
        session.publish_vulnerability_report(json_payload(session.lookup_vulnerabilities()))
        session.publish_candidate_strategies(json_payload(fixture_candidates(["CVE-2021-44228"])))
        session.build_argumentation_graph()
        if stage == "ranking":
            session.ranking_tool = Unavailable()
            call = session.rank_graph
        else:
            session.rank_graph()
            session.semantic_tool = Unavailable()

            def call():
                return session.validate_countermeasure("S_UPGRADE")

    before = {p.name: p.read_bytes() for p in session.output_dir.glob("*.json")}
    with pytest.raises(TimeoutError, match=f"{stage} unavailable"):
        call()
    assert {p.name: p.read_bytes() for p in session.output_dir.glob("*.json")} == before
    assert "final_decision" not in session.get_context()["artifacts"]
    # Il backend può recuperare sulla stessa fase, senza perdere gli input validati.
    session.vulnerability_tool = MockVulnerabilityTool()
    session.ranking_tool = MockRankingTool()
    session.semantic_tool = MockSemanticTool()
    assert call()


def test_empty_backend_ranking_for_nonempty_candidates_is_a_failure(session):
    class EmptyRanking:
        def rank_graph(self, graph):
            return RankingResult(graph_id=graph.id, backend="invalid-test-backend", ranking=[])

    session.publish_runtime_evidence(json_payload(fixture_evidence(session)))
    session.publish_vulnerability_report(json_payload(session.lookup_vulnerabilities()))
    session.publish_candidate_strategies(json_payload(fixture_candidates(["CVE-2021-44228"])))
    session.build_argumentation_graph()
    session.ranking_tool = EmptyRanking()
    with pytest.raises(ValueError, match="candidate set"):
        session.rank_graph()
    assert "ranking" not in session.get_context()["artifacts"]
    assert not (session.output_dir / "ranking.json").exists()


def test_technical_lookup_failure_blocks_downstream_agents(case, tmp_path):
    class UnavailableLookup:
        def lookup_vulnerabilities(self, software):
            raise TimeoutError("backend unavailable")

    session = ArtifactSession(case, tmp_path, vulnerability_tool=UnavailableLookup())
    model = ScriptedToolModel(session)
    workforce = build_workforce(session, lambda: model)
    from camel.tasks import Task
    from camel.tasks.task import TaskState

    result = workforce.process_task(Task(id="main", content="Execute the configured pipeline"))
    assert result.state == TaskState.FAILED
    assert set(workforce.blocked_tasks) == {"countermeasure", "strategic"}
    assert set(model.steps) == {"telemetry", "vulnerability"}
    assert set(session.get_context()["artifacts"]) == {"input", "runtime_evidence"}
