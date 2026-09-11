# Test delle regole di dominio indipendenti dall'inferenza LLM.
# Usano fixture esplicite e directory temporanee, verificando sia il percorso di
# successo sia errori che un output generato potrebbe introdurre. Le alterazioni
# di _artifacts presenti in alcuni test simulano corruzioni intenzionali dello stato;
# non rappresentano un'API supportata per gli agenti o il codice applicativo.
import hashlib
import json

import pytest
from pydantic import ValidationError

from thesis_agents.fixtures import fixture_candidates, fixture_evidence, run_fixtures
from thesis_agents.orchestration.artifacts import ARTIFACT_SCHEMAS, ArtifactSession, json_payload
from thesis_agents.schemas import (
    CandidateStrategies,
    FinalDecision,
    ProvenanceRecord,
    RankingResult,
    RuntimeEvidence,
    SemanticValidationReport,
    StaticTelemetry,
    VulnerabilityReport,
)
from thesis_agents.schemas.argumentation import RankedStrategy
from thesis_agents.tools.ranking_mock import MockRankingTool, build_graph


def prepare(session):
    # Porta una sessione fino al ranking senza selezionare alcuna strategia.
    # È il punto comune da cui molti test esercitano validazione e decisione.
    session.publish_runtime_evidence(json_payload(fixture_evidence(session)))
    report = session.lookup_vulnerabilities()
    session.publish_vulnerability_report(json_payload(report))
    session.publish_candidate_strategies(json_payload(fixture_candidates(["CVE-2021-44228"])))
    session.build_argumentation_graph()
    session.rank_graph()


def test_full_fixture_run_and_provenance_hashes(session):
    # Verifica l'intero contratto: strategia attesa, otto JSON validi, digest dei file
    # e riferimenti delle attività. Il record deve dichiarare esplicitamente fixtures.
    decision = run_fixtures(session)
    assert decision.selected_strategy_id == "S_UPGRADE"
    assert decision.ranking[0].score == 0.875
    for name, schema in ARTIFACT_SCHEMAS.items():
        schema.model_validate_json((session.output_dir / f"{name}.json").read_text())
    provenance = session.require("provenance", ProvenanceRecord)
    assert provenance.mode == "fixtures"
    assert all(agent.startswith("fixture:") for agent in provenance.agents)
    assert len(provenance.entities) == 8  # Seven domain outputs plus the input.
    entities = {e.id for e in provenance.entities}
    for entity in provenance.entities:
        assert (
            hashlib.sha256((session.output_dir / entity.filename).read_bytes()).hexdigest()
            == entity.sha256
        )
    for activity in provenance.activities:
        assert set(activity.used + activity.generated) <= entities
    assert session.record_provenance()["stored"]


def test_rejected_best_candidate_falls_back(case, tmp_path):
    # Manca una condizione dell'upgrade, non il beneficio stimato: resta primo nel
    # ranking ma viene rifiutato semanticamente. Il secondo viene provato e selezionato.
    case.available_capabilities.remove("maintenance_window")
    session = ArtifactSession(case, tmp_path, mode="fixtures")
    decision = run_fixtures(session)
    assert decision.selected_strategy_id == "S_ISOLATE"
    attempts = session.require("semantic_validation", SemanticValidationReport).validations
    assert [(v.strategy_id, v.valid) for v in attempts] == [
        ("S_UPGRADE", False),
        ("S_ISOLATE", True),
    ]
    assert attempts[0].missing_requirements == ["maintenance_window"]


def test_all_candidates_rejected(case, tmp_path):
    # Senza capacità non deve comparire una selezione arbitraria. Si conservano
    # quattro tentativi falliti per spiegare l'esito no_valid_strategy.
    case.available_capabilities = []
    session = ArtifactSession(case, tmp_path, mode="fixtures")
    result = run_fixtures(session)
    assert result.status == "no_valid_strategy"
    assert result.selected_strategy_id is None
    assert len(session.require("semantic_validation", SemanticValidationReport).validations) == 4


def test_policy_can_reject_otherwise_feasible_strategy(case, tmp_path):
    # Capacità e policy sono vincoli distinti: le prime due azioni sono realizzabili
    # nel caso ma proibite, quindi il flusso deve arrivare alla terza alternativa.
    case.prohibited_actions = ["upgrade", "isolate"]
    session = ArtifactSession(case, tmp_path, mode="fixtures")
    assert run_fixtures(session).selected_strategy_id == "S_BLOCK"


def test_unknown_version_is_inconclusive_not_safe(case, tmp_path):
    # Una versione fuori dalla fixture deve produrre insufficient_evidence,
    # classifica vuota e nessuna validazione scelta; non una dichiarazione di sicurezza.
    case.package_version = "99.0.0"
    session = ArtifactSession(case, tmp_path, mode="fixtures")
    result = run_fixtures(session)
    assert result.status == "insufficient_evidence"
    assert result.ranking == []
    assert result.semantic_validation is None
    assert session.require("candidate_strategies", CandidateStrategies).strategies == []


@pytest.mark.parametrize("score", [-0.1, 1.1, float("nan"), float("inf")])
def test_invalid_estimates_rejected(score):
    # Parametrize esegue lo stesso controllo con quattro valori invalidi: entrambi
    # i lati dell'intervallo ammesso e numeri non finiti che altererebbero l'ordinamento.
    data = fixture_candidates(["CVE-2021-44228"]).model_dump()
    data["strategies"][0]["security_benefit"] = score
    with pytest.raises(ValidationError):
        CandidateStrategies.model_validate(data)


def test_duplicate_candidate_ids_rejected():
    # Due proposte con lo stesso ID renderebbero ambigui grafo e selezione.
    # Si modifica un dizionario prima della validazione per simulare un payload LLM.
    data = fixture_candidates(["CVE-2021-44228"]).model_dump()
    data["strategies"][1]["id"] = data["strategies"][0]["id"]
    with pytest.raises(ValidationError, match="Duplicate"):
        CandidateStrategies.model_validate(data)


def test_input_rejects_extra_fields_and_string_booleans(case):
    # Controlla la rigidità del contratto: non si convertono silenziosamente stringhe
    # in fatti booleani e non si ignorano campi non previsti nello schema.
    for changes in ({"endpoint_exposed": "false"}, {"unrecognized": True}):
        with pytest.raises(ValidationError):
            StaticTelemetry.model_validate(case.model_dump() | changes)


def test_mutated_telemetry_facts_rejected(session):
    # Il JSON è formalmente valido ma cambia la versione: il controllo trasversale
    # della sessione deve rifiutarlo confrontandolo con l'input originale.
    data = fixture_evidence(session).model_dump()
    data["software"][0]["version"] = "2.17.1"
    with pytest.raises(ValueError, match="preserve"):
        session.publish_runtime_evidence(json_payload(data))


def test_unknown_cve_or_changed_backend_scores_rejected(session):
    # Prova due falsificazioni diverse: alterare il finding restituito dal tool
    # e generare una candidata che afferma di affrontare una CVE assente dal report.
    session.publish_runtime_evidence(json_payload(fixture_evidence(session)))
    report = session.lookup_vulnerabilities()
    report["vulnerabilities"][0]["cvss"] = 1.0
    with pytest.raises(ValueError, match="exact report"):
        session.publish_vulnerability_report(json_payload(report))
    session.publish_vulnerability_report(json_payload(session.lookup_vulnerabilities()))
    with pytest.raises(ValueError, match="unknown vulnerability"):
        session.publish_candidate_strategies(json_payload(fixture_candidates(["CVE-2099-9999"])))


def test_missing_stages_and_skipped_validation_rejected(session):
    # Verifica che non si possa anticipare il ranking, saltare il primo candidato,
    # dichiarare fallimento senza tentativi o selezionare un'alternativa non accettata.
    with pytest.raises(ValueError, match="Missing prerequisite"):
        session.rank_graph()
    prepare(session)
    with pytest.raises(ValueError, match="without skipping"):
        session.validate_countermeasure("S_ISOLATE")
    with pytest.raises(ValueError, match="every ranked strategy"):
        session.publish_final_decision(None, "No candidate")
    session.validate_countermeasure("S_UPGRADE")
    with pytest.raises(ValueError, match="exactly the first"):
        session.publish_final_decision("S_ISOLATE", "Overriding the ranking")


def test_accepted_candidate_stops_validation_and_retries_are_idempotent(session):
    # Ripetere la richiesta sullo stesso ID restituisce l'esito già noto; chiedere
    # una nuova validazione dopo il primo successo viola invece la regola di selezione.
    prepare(session)
    a = session.validate_countermeasure("S_UPGRADE")
    assert a == session.validate_countermeasure("S_UPGRADE")
    assert len(session.require("semantic_validation", SemanticValidationReport).validations) == 1
    with pytest.raises(ValueError, match="already been found"):
        session.validate_countermeasure("S_ISOLATE")


def test_llm_cannot_bypass_backend_prerequisites(case, tmp_path):
    # Rimuovere dalla candidata i prerequisiti non deve rimuovere quelli obbligatori
    # del backend: l'upgrade continua a richiedere una finestra di manutenzione.
    case.available_capabilities.remove("maintenance_window")
    session = ArtifactSession(case, tmp_path, mode="fixtures")
    session.publish_runtime_evidence(json_payload(fixture_evidence(session)))
    session.publish_vulnerability_report(json_payload(session.lookup_vulnerabilities()))
    candidates = fixture_candidates(["CVE-2021-44228"])
    candidates.strategies[0].prerequisites = []
    session.publish_candidate_strategies(json_payload(candidates))
    session.build_argumentation_graph()
    session.rank_graph()
    assert session.validate_countermeasure("S_UPGRADE")["valid"] is False


def test_ranking_is_order_independent_and_ties_are_stable():
    # Porta tutte le candidate a pari score e inverte nodi/archi. Il risultato deve
    # mantenere il tie-break per ID, anziché dipendere dall'ordine dei dati in ingresso.
    candidates = fixture_candidates(["CVE-2021-44228"])
    for candidate in candidates.strategies:
        candidate.security_benefit = 0.8
        candidate.operational_impact = 0.2
    graph = build_graph(candidates, "G1")
    tool = MockRankingTool()
    first = tool.rank_graph(graph)
    graph.arguments.reverse()
    graph.relations.reverse()
    assert tool.rank_graph(graph) == first
    assert [r.strategy_id for r in first.ranking] == sorted(s.id for s in candidates.strategies)


def test_unrelated_backend_ranking_is_rejected(session):
    # Un backend sostitutivo può restituire dati Pydantic validi ma estranei al caso.
    # Il confronto con le candidate del grafo deve intercettare anche questo errore.
    class BadRanking:
        # Double locale intenzionalmente scorretto, usato soltanto da questo test.
        def rank_graph(self, graph):
            return RankingResult(
                graph_id=graph.id,
                backend="bad-test-backend",
                ranking=[RankedStrategy(strategy_id="INVENTED", score=1)],
            )

    session.ranking_tool = BadRanking()
    with pytest.raises(ValueError, match="unrelated graph or candidate set"):
        prepare(session)


def test_publication_immutable_and_output_not_overwritten(session):
    # Verifica insieme retry identico, rifiuto della riscrittura e protezione di una
    # directory già utilizzata. La prima pubblicazione resta la fonte autorevole.
    evidence = fixture_evidence(session)
    payload = evidence.model_dump_json()
    session.publish_runtime_evidence(payload)
    assert session.publish_runtime_evidence(payload) == json.loads(payload)
    evidence.observations = ["Changed observation"]
    with pytest.raises(ValueError, match="immutable"):
        session.publish_runtime_evidence(evidence.model_dump_json())
    with pytest.raises(ValueError, match="must be empty"):
        ArtifactSession(session.case, session.output_dir)


def test_fake_success_without_provenance_is_not_complete(session):
    # Una decisione esistente non è una prova di completamento del run: deve esserci
    # anche la provenienza. Il controllo finale non si basa solo sull'ultimo output.
    prepare(session)
    session.validate_countermeasure("S_UPGRADE")
    session.publish_final_decision("S_UPGRADE", "Grounded in local tool outputs")
    with pytest.raises(ValueError, match="provenance"):
        session.assert_complete()


def test_decision_cannot_claim_selection_without_validation():
    # Verifica lo schema isolato, prima ancora dei controlli fra artefatti:
    # lo stato selected richiede una validazione semantica positiva associata.
    with pytest.raises(ValidationError, match="accepted semantic validation"):
        FinalDecision(
            status="selected",
            selected_strategy_id="S_UPGRADE",
            ranking=[],
            semantic_validation=None,
            evidence_ids=["E1"],
            explanation="Unsupported claim",
        )


def test_runtime_evidence_survives_as_a_separate_artifact_until_decision(session):
    # Salva i byte iniziali dell'evidenza e li confronta dopo la decisione. Controlla
    # anche copie del contesto e attività di provenienza: la convergenza degli input
    # nello StrategicAgent non deve cancellare i tre produttori distinti.
    evidence = fixture_evidence(session)
    session.publish_runtime_evidence(evidence.model_dump_json())
    original_bytes = (session.output_dir / "runtime_evidence.json").read_bytes()
    report = session.lookup_vulnerabilities()
    session.publish_vulnerability_report(json_payload(report))
    assert session.require("runtime_evidence", RuntimeEvidence) == evidence
    assert session.require("vulnerability_report", VulnerabilityReport).model_dump() == report

    run_fixtures(session)
    context = session.get_context()
    assert context["artifacts"]["runtime_evidence"] == evidence.model_dump()
    assert context["artifacts"]["vulnerability_report"] == report
    assert (session.output_dir / "runtime_evidence.json").read_bytes() == original_bytes
    assert context["artifact_producers"] == {
        "runtime_evidence": "fixture:TelemetryAgent",
        "vulnerability_report": "fixture:VulnerabilityAgent",
        "candidate_strategies": "fixture:CountermeasureAgent",
    }
    # A consumer cannot mutate the session through the returned context dictionary.
    context["artifacts"]["runtime_evidence"]["software"][0]["version"] = "changed"
    assert session.require("runtime_evidence", RuntimeEvidence) == evidence
    provenance = session.require("provenance", ProvenanceRecord)
    decision_activity = next(a for a in provenance.activities if a.id == "decision")
    assert set(decision_activity.used) == {
        "runtime_evidence",
        "vulnerability_report",
        "candidate_strategies",
        "ranking",
        "semantic_validation",
    }
    for artifact, producer in context["artifact_producers"].items():
        activity = next(a for a in provenance.activities if artifact in a.generated)
        assert activity.agent == producer


def test_report_cannot_embed_or_replace_runtime_evidence(session):
    # Un report con evidence annidata viene rifiutato come campo aggiuntivo; una
    # RuntimeEvidence spacciata per report fallisce per schema. L'evidenza resta intatta.
    evidence = fixture_evidence(session)
    session.publish_runtime_evidence(evidence.model_dump_json())
    report = session.lookup_vulnerabilities()
    with pytest.raises(ValidationError, match="Extra inputs"):
        session.publish_vulnerability_report(
            json_payload(report | {"runtime_evidence": evidence.model_dump()})
        )
    with pytest.raises(ValidationError):
        session.publish_vulnerability_report(evidence.model_dump_json())
    assert session.require("runtime_evidence", RuntimeEvidence) == evidence
    assert "vulnerability_report" not in session.get_context()["artifacts"]


@pytest.mark.parametrize(
    "missing",
    [
        "runtime_evidence",
        "vulnerability_report",
        "candidate_strategies",
    ],
)
@pytest.mark.parametrize("stage", ["graph", "decision"])
def test_strategic_stages_require_each_distinct_input(session, missing, stage):
    # Il prodotto cartesiano dei parametri copre tre input per due stadi strategici.
    # Anche con ranking e validazione già esistenti, perdere un input deve bloccare
    # la costruzione del grafo o la decisione anziché usare soltanto i dati derivati.
    prepare(session)
    session.validate_countermeasure("S_UPGRADE")
    # Simulate missing shared state even though downstream artifacts already exist.
    session._artifacts.pop(missing)
    with pytest.raises(ValueError, match=f"Missing prerequisite artifact: {missing}"):
        if stage == "graph":
            session.build_argumentation_graph()
        else:
            session.publish_final_decision("S_UPGRADE", "Cannot decide from partial inputs")
    assert not (session.output_dir / "final_decision.json").exists()


@pytest.mark.parametrize("stage", ["lookup", "report", "candidates"])
def test_runtime_evidence_is_required_even_when_a_report_is_cached(session, stage):
    # La cache del lookup non elimina la dipendenza dalla telemetria. La verifica
    # riguarda lookup, pubblicazione del report e pubblicazione delle candidate.
    prepare(session)
    session._artifacts.pop("runtime_evidence")
    with pytest.raises(ValueError, match="Missing prerequisite artifact: runtime_evidence"):
        if stage == "lookup":
            session.lookup_vulnerabilities()
        elif stage == "report":
            session.publish_vulnerability_report(session._lookup.model_dump_json())
        else:
            session.publish_candidate_strategies(
                fixture_candidates(["CVE-2021-44228"]).model_dump_json()
            )


def test_final_decision_rechecks_the_candidate_artifact(session):
    # Una classifica o validazione pregressa non autorizza a scegliere una strategia
    # che non compare più nell'artefatto delle candidate: è una incoerenza del run.
    prepare(session)
    session.validate_countermeasure("S_UPGRADE")
    # Simulate inconsistent downstream state; an accepted validation is not sufficient.
    candidates = session.require("candidate_strategies", CandidateStrategies)
    candidates.strategies = candidates.strategies[1:]
    session._artifacts["candidate_strategies"] = candidates
    with pytest.raises(ValueError, match="must match the published candidate strategies"):
        session.publish_final_decision("S_UPGRADE", "Cannot select a missing candidate")
