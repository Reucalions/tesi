# Test di integrazione SDK: gli agenti e la Workforce sono quelli reali di CAMEL,
# ma il backend di inferenza risponde secondo uno script locale. Questo verifica
# scheduling, tool calling e consegna degli artefatti, non l'intelligenza del modello.
# Nessun mock di produzione viene modificato per rendere il test deterministico.
"""Real CAMEL orchestration and tool dispatch, scripted inference ONLY for testing.

This verifies SDK integration without a network call. It is not an LLM evaluation.
"""

import ast
import asyncio
import json
import re
from collections import defaultdict

import pytest
from camel.models.stub_model import StubModel
from camel.societies.workforce import Workforce
from camel.societies.workforce.workforce import WorkforceMode
from camel.tasks import Task
from camel.tasks.task import TaskState
from camel.types import ChatCompletion, ModelType

from thesis_agents.fixtures import fixture_candidates, fixture_evidence
from thesis_agents.orchestration.artifacts import ArtifactSession
from thesis_agents.orchestration.workforce import build_workforce, run_camel
from thesis_agents.schemas import (
    CandidateStrategies,
    RuntimeEvidence,
    SemanticValidationReport,
    VulnerabilityReport,
)


class ScriptedToolModel(StubModel):
    # Backend solo di test con la stessa interfaccia sincrona/asincrona dell'SDK.
    # Genera richieste di tool: è poi ChatAgent a eseguirle davvero sulla sessione.
    def __init__(self, session):
        # steps tiene il prossimo passo per ruolo; tool_calls registra le richieste;
        # received_contexts conserva ciò che il modello riceve realmente da CAMEL.
        super().__init__(ModelType.STUB)
        self.session = session
        self.steps = defaultdict(int)
        self.tool_calls = []
        self.received_contexts = {}

    @property
    def token_limit(self):
        # The SDK stub defaults to a tiny window that drops get_context's schemas.
        # Keep tool responses in memory so this test observes the actual handoff.
        return 128_000

    def _run(self, messages, response_format=None, tools=None):
        # La lista dei tool identifica il ruolo senza dipendere dal suo UUID casuale.
        # I modelli gestionali non hanno tool e ricevono invece un prompt di assegnazione.
        tool_names = {t["function"]["name"] for t in tools or []}
        if not tool_names:
            # Estrae gli ID dei worker dal prompt creato dall'SDK. Non si hardcodano
            # UUID, così il test attraversa l'assegnazione della Workforce effettiva.
            prompt = messages[-1]["content"]
            workers = dict(re.findall(r"<([^>]+)>:<([A-Za-z]+Agent):", prompt))
            roles = {role: id_ for id_, role in workers.items()}
            tasks = re.findall(r"Task ID: ([^\n]+)\nContent: ([A-Za-z]+Agent):", prompt)
            assert tasks and roles, f"Unexpected management request: {prompt[:160]}"
            payload = {
                "assignments": [
                    {"task_id": task_id, "assignee_id": roles[role], "dependencies": []}
                    for task_id, role in tasks
                ]
            }
            return self._completion(content=json.dumps(payload))

        if "publish_runtime_evidence" in tool_names:
            # Ogni ruolo prima chiama get_context, poi esegue le proprie pubblicazioni.
            # I payload prefissati sostituiscono solo la generazione dei dati nel test.
            role = "telemetry"
            script = [
                ("get_context", {}),
                (
                    "publish_runtime_evidence",
                    {"payload": fixture_evidence(self.session).model_dump(mode="json")},
                ),
            ]
        elif "publish_vulnerability_report" in tool_names:
            role = "vulnerability"
            script = [("get_context", {}), ("lookup_vulnerabilities", {})]
            if self.session._lookup is not None:
                # Il report può essere preparato solo dopo l'esecuzione del lookup:
                # il test non riempie la cache né chiama direttamente il backend KG.
                script.append(
                    (
                        "publish_vulnerability_report",
                        {"payload": self.session._lookup.model_dump(mode="json")},
                    )
                )
        elif "publish_candidate_strategies" in tool_names:
            role = "countermeasure"
            report = self.session.require("vulnerability_report", VulnerabilityReport)
            script = [
                ("get_context", {}),
                (
                    "publish_candidate_strategies",
                    {
                        "payload": fixture_candidates(
                            [v.cve_id for v in report.vulnerabilities]
                        ).model_dump(mode="json")
                    },
                ),
            ]
        else:
            role = "strategic"
            unsupported = (
                self.session.require("vulnerability_report", VulnerabilityReport).lookup_status
                == "unsupported"
            )
            script = [
                ("get_context", {}),
                ("build_argumentation_graph", {}),
                ("rank_graph", {}),
                # Senza candidate il modello deve pubblicare direttamente null;
                # il tool finale crea anche il report semantico vuoto.
                *(
                    []
                    if unsupported
                    else [("validate_countermeasure", {"strategy_id": "S_UPGRADE"})]
                ),
                (
                    "publish_final_decision",
                    {
                        "selected_strategy_id": None if unsupported else "S_UPGRADE",
                        "explanation": "Scripted inference test; real CAMEL tool dispatch.",
                    },
                ),
                ("record_provenance", {}),
            ]
        step = self.steps[role]
        if step == 1:
            # Verifica il vero messaggio di risposta del tool nella memoria passata
            # al modello. Leggere qui session.get_context() aggirerebbe la consegna SDK
            # e non dimostrerebbe che lo StrategicAgent abbia ricevuto i tre artefatti.
            # Inspect what CAMEL actually delivered to the model after get_context,
            # rather than reading ArtifactSession directly in this assertion.
            context_messages = [message for message in messages if message.get("role") == "tool"]
            assert context_messages, "CAMEL must deliver the get_context tool response"
            context_message = context_messages[-1]
            content = context_message["content"]
            try:
                self.received_contexts[role] = json.loads(content)
            except json.JSONDecodeError:
                # L'SDK può rendere il risultato come rappresentazione di un dict
                # Python. literal_eval legge solo letterali, senza eseguire codice.
                self.received_contexts[role] = ast.literal_eval(content)
        self.steps[role] += 1
        if step >= len(script):
            # Un TaskResult gestionale minimale consente a CAMEL di chiudere il task.
            # Gli output autorevoli sono già stati pubblicati tramite i tool precedenti.
            return self._completion(content=json.dumps({"content": "{}", "failed": False}))
        name, arguments = script[step]
        self.tool_calls.append(name)
        return self._completion(
            tool_calls=[
                {
                    "id": f"call-{role}-{step}",
                    "type": "function",
                    "function": {"name": name, "arguments": json.dumps(arguments)},
                }
            ]
        )

    async def _arun(self, messages, response_format=None, tools=None):
        # Le chiamate asincrone dei worker usano lo stesso script deterministico.
        return self._run(messages, response_format, tools)

    @staticmethod
    def _completion(content=None, tool_calls=None):
        # Costruisce una risposta nel formato ChatCompletion atteso da CAMEL.
        # finish_reason distingue una richiesta di tool da una risposta conclusiva;
        # token e timestamp sono fittizi e non misurano un'effettiva inferenza.
        message = {"role": "assistant", "content": content}
        if tool_calls:
            message["tool_calls"] = tool_calls
        return ChatCompletion.model_validate(
            {
                "id": "scripted-test",
                "model": "stub",
                "object": "chat.completion",
                "created": 0,
                "choices": [
                    {
                        "index": 0,
                        "finish_reason": "tool_calls" if tool_calls else "stop",
                        "message": message,
                    }
                ],
                "usage": {"prompt_tokens": 10, "completion_tokens": 10, "total_tokens": 20},
            }
        )


def test_real_workforce_dispatches_four_agents_and_publishes_artifacts(case, tmp_path):
    # Attraversa tutti i worker e confronta i tre modelli arrivati allo StrategicAgent
    # con gli artefatti validati, controllando anche produttori e conservazione di evidence.
    session = ArtifactSession(case, tmp_path, mode="camel", model="scripted-test-only")
    backend = ScriptedToolModel(session)
    result = run_camel(session, lambda: backend)
    assert result.selected_strategy_id == "S_UPGRADE"
    assert result.explanation_method == "artifact-derived-v1"
    assert result.agent_commentary.text == "Scripted inference test; real CAMEL tool dispatch."
    assert result.agent_commentary.text not in result.explanation
    producers = {s.producer for c in result.explanation_claims for s in c.sources}
    assert producers == {
        "StaticTelemetry",
        "TelemetryAgent",
        "VulnerabilityAgent",
        "CountermeasureAgent",
        "StrategicAgent",
    }
    assert set(backend.steps) == {"telemetry", "vulnerability", "countermeasure", "strategic"}
    assert backend.tool_calls.count("lookup_vulnerabilities") == 1
    assert backend.tool_calls.count("rank_graph") == 1
    assert backend.tool_calls.count("record_provenance") == 1
    context = backend.received_contexts["strategic"]
    expected = {
        "runtime_evidence": (RuntimeEvidence, "TelemetryAgent"),
        "vulnerability_report": (VulnerabilityReport, "VulnerabilityAgent"),
        "candidate_strategies": (CandidateStrategies, "CountermeasureAgent"),
    }
    for name, (schema, producer) in expected.items():
        assert schema.model_validate(context["artifacts"][name]) == session.require(name, schema)
        assert context["artifact_producers"][name] == producer
    runtime = context["artifacts"]["runtime_evidence"]
    assert runtime == backend.received_contexts["vulnerability"]["artifacts"]["runtime_evidence"]
    assert runtime == backend.received_contexts["countermeasure"]["artifacts"]["runtime_evidence"]
    assert (
        context["artifacts"]["vulnerability_report"]
        == (backend.received_contexts["countermeasure"]["artifacts"]["vulnerability_report"])
    )
    assert result.evidence_ids == [s["evidence_id"] for s in runtime["software"]]


def test_real_workforce_completes_unsupported_lookup_without_validation(case, tmp_path):
    # Regressione del percorso vuoto osservato con Ollama: esegue davvero i tool
    # CAMEL, ma lo script non dimostra che un LLM seguirà il prompt corretto.
    case.package_name = "demo-unsupported-package"
    session = ArtifactSession(case, tmp_path, mode="camel", model="scripted-test-only")
    backend = ScriptedToolModel(session)
    result = run_camel(session, lambda: backend)
    assert result.status == "insufficient_evidence"
    assert result.selected_strategy_id is None
    assert result.ranking == []
    assert "validate_countermeasure" not in backend.tool_calls
    assert backend.tool_calls.count("publish_final_decision") == 1
    assert backend.tool_calls.count("record_provenance") == 1
    assert session.require("semantic_validation", SemanticValidationReport).validations == []
    context = backend.received_contexts["strategic"]
    assert context["artifacts"]["vulnerability_report"]["lookup_status"] == "unsupported"
    assert context["artifacts"]["candidate_strategies"]["strategies"] == []
    assert context["artifacts"]["runtime_evidence"]["software"][0]["package"] == case.package_name
    assert session.assert_complete() == result


def test_default_pipeline_has_explicit_producer_dependencies(case, tmp_path):
    # Ispeziona task e mappa interna dello scheduler: verificare soltanto la costante
    # TASK_DEPENDENCIES non proverebbe che gli archi siano stati passati a CAMEL.
    session = ArtifactSession(case, tmp_path, mode="camel", model="scripted-test-only")
    workforce = build_workforce(session, lambda: ScriptedToolModel(session))
    assert workforce.mode == WorkforceMode.PIPELINE
    expected = {
        "telemetry": [],
        "vulnerability": ["telemetry"],
        "countermeasure": ["telemetry", "vulnerability"],
        "strategic": ["telemetry", "vulnerability", "countermeasure"],
    }
    # Check both the task objects and CAMEL's actual scheduling dependency map.
    assert {t.id: [d.id for d in t.dependencies] for t in workforce._pending_tasks} == expected
    assert workforce._task_dependencies == expected


@pytest.mark.parametrize(
    "failed_role,blocked",
    [
        ("telemetry", {"vulnerability", "countermeasure", "strategic"}),
        ("vulnerability", {"countermeasure", "strategic"}),
        ("countermeasure", {"strategic"}),
    ],
)
def test_pipeline_blocks_descendants_after_producer_exhausts_retries(
    case, tmp_path, failed_role, blocked
):
    class FailingProducer(ScriptedToolModel):
        failures = 0
        invoked_roles = set()

        def _run(self, messages, response_format=None, tools=None):
            names = {t["function"]["name"] for t in tools or []}
            for role, publication in (
                ("telemetry", "publish_runtime_evidence"),
                ("vulnerability", "publish_vulnerability_report"),
                ("countermeasure", "publish_candidate_strategies"),
                ("strategic", "publish_final_decision"),
            ):
                if publication in names:
                    self.invoked_roles.add(role)
                    if role == failed_role:
                        self.failures += 1
                        return self._completion(
                            content='{"content":"Cannot publish","failed":true}'
                        )
            return super()._run(messages, response_format, tools)

    session = ArtifactSession(case, tmp_path, mode="camel", model="scripted-test-only")
    backend = FailingProducer(session)
    workforce = build_workforce(session, lambda: backend)
    result = workforce.process_task(Task(id="main", content="Execute the configured pipeline"))
    assert result.state == TaskState.FAILED
    assert backend.failures == 2
    assert backend.invoked_roles.isdisjoint(blocked)
    assert set(workforce.blocked_tasks) == blocked
    assert failed_role in workforce.failure_description()
    assert "Task bloccati" in workforce.failure_description()
    assert not (tmp_path / "final_decision.json").exists()
    assert not workforce._pending_tasks


@pytest.mark.parametrize("workflow", ["pipeline", "auto"])
def test_worker_checks_missing_artifacts_before_llm(case, tmp_path, workflow):
    class MustNotInfer(ScriptedToolModel):
        def _run(self, messages, response_format=None, tools=None):
            pytest.fail("A worker without prerequisites must not invoke the LLM")

    session = ArtifactSession(case, tmp_path, mode="camel", model="scripted-test-only")
    workforce = build_workforce(session, lambda: MustNotInfer(session), workflow=workflow)
    worker = workforce._children[1]
    task = Task(id="vulnerability", content="Look up vulnerabilities")
    assert asyncio.run(worker._process_task(task, [])) == TaskState.FAILED
    assert "Missing prerequisite artifact: runtime_evidence" in task.result


def test_blocking_preserves_independent_tasks(case, tmp_path, monkeypatch):
    session = ArtifactSession(case, tmp_path, mode="camel", model="scripted-test-only")
    workforce = build_workforce(session, lambda: ScriptedToolModel(session))
    telemetry_task = workforce._pending_tasks.popleft()
    telemetry_task.state = TaskState.FAILED
    workforce._completed_tasks.append(telemetry_task)
    independent = Task(id="independent", content="Independent task", state=TaskState.OPEN)
    workforce._pending_tasks.append(independent)
    workforce._task_dependencies[independent.id] = []

    async def inspect_ready_tasks(self):
        # Il filtro deve consegnare allo scheduler SDK il ramo indipendente.
        assert list(self._pending_tasks) == [independent]

    monkeypatch.setattr(Workforce, "_post_ready_tasks", inspect_ready_tasks)
    asyncio.run(workforce._post_ready_tasks())
    assert set(workforce.blocked_tasks) == {"vulnerability", "countermeasure", "strategic"}
    assert independent.state != TaskState.FAILED


def test_camel_worker_rejects_success_without_artifact(case, tmp_path):
    """Attraversa il worker reale: il suo TaskResult non deve diventare DONE."""

    class FalseSuccessModel(ScriptedToolModel):
        def _run(self, messages, response_format=None, tools=None):
            return self._completion(
                content='{"content": "Published the runtime evidence", "failed": false}'
            )

    session = ArtifactSession(case, tmp_path, mode="camel", model="scripted-test-only")
    workforce = build_workforce(session, lambda: FalseSuccessModel(session))
    worker = workforce._children[0]
    task = Task(id="telemetry", content="Publish runtime evidence")
    state = asyncio.run(worker._process_task(task, []))
    assert state == TaskState.FAILED
    assert not (tmp_path / "runtime_evidence.json").exists()


def test_pipeline_retries_missing_publications_without_replacing_evidence(case, tmp_path):
    class EarlyExitModel(ScriptedToolModel):
        stopped_early = False
        retry_read_context = False

        def _run(self, messages, response_format=None, tools=None):
            names = {t["function"]["name"] for t in tools or []}
            if "publish_final_decision" in names and self.steps["strategic"] == 4:
                if not self.stopped_early:
                    self.stopped_early = True
                    self.before_retry = {
                        p.name: p.read_bytes() for p in self.session.output_dir.glob("*.json")
                    }
                    return self._completion(content='{"content": "Done", "failed": false}')
                if not self.retry_read_context:
                    assert (
                        "Remaining artifacts: final_decision, provenance" in messages[-1]["content"]
                    )
                    self.retry_read_context = True
                    return self._completion(
                        tool_calls=[
                            {
                                "id": "retry-context",
                                "type": "function",
                                "function": {"name": "get_context", "arguments": "{}"},
                            }
                        ]
                    )
            return super()._run(messages, response_format, tools)

    session = ArtifactSession(case, tmp_path, mode="camel", model="scripted-test-only")
    backend = EarlyExitModel(session)
    result = run_camel(session, lambda: backend)
    assert result.selected_strategy_id == "S_UPGRADE"
    assert backend.retry_read_context
    assert backend.tool_calls.count("rank_graph") == 1
    assert backend.tool_calls.count("record_provenance") == 1
    for name, content in backend.before_retry.items():
        assert (tmp_path / name).read_bytes() == content
