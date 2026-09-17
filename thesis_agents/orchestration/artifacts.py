# Stato autorevole di un singolo run e confine fra agenti e backend sostituibili.
# I tool pubblici validano JSON, applicano i vincoli fra artefatti e salvano file.
# Gli agenti non modificano direttamente lo stato: usano pubblicazioni per ruolo
# e leggono copie serializzate con get_context. Le docstring dei tool sono anche
# usate da CAMEL per descriverli al modello; le spiegazioni aggiuntive sono commenti.
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import TypeVar
from uuid import uuid4

from pydantic import BaseModel

from thesis_agents.orchestration.explanations import build_explanation
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
from thesis_agents.schemas.decision import AgentCommentary
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

# T conserva per il type checker il tipo del modello passato a require/_commit.
T = TypeVar("T", bound=BaseModel)
# Registro degli otto output: usato per esportare gli schemi e verificare il run.
# input.json è una copia aggiuntiva dell'ingresso, non uno degli otto risultati.
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

# Produttori dei tre input strategici: metadati del contesto, non nuovi artefatti.
# La provenienza completa viene registrata separatamente dopo la decisione.
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
        # Una directory non vuota potrebbe contenere risultati di un altro run:
        # si rifiuta il riuso, così non si mescolano evidenze e decisioni precedenti.
        if mode not in ("camel", "fixtures"):
            raise ValueError("Unknown execution mode")
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)
        if any(output_dir.iterdir()):
            raise ValueError(f"Output directory must be empty: {output_dir}")
        self.output_dir = output_dir
        self.case = case.model_copy(deep=True)
        # La copia profonda separa l'input interno da eventuali modifiche del chiamante.
        self.mode = mode
        self.model = model
        self.run_id = f"run-{uuid4().hex}"
        self.created_at = datetime.now(UTC).isoformat()
        self.vulnerability_tool = vulnerability_tool or MockVulnerabilityTool()
        # Dependency injection: i backend forniti rispettano i Protocol del progetto.
        # In loro assenza si usano i mock; gli agenti invocano le stesse interfacce.
        self.ranking_tool = ranking_tool or MockRankingTool()
        self.semantic_tool = semantic_tool or MockSemanticTool()
        self.provenance_tool = provenance_tool or MockProvenanceTool(output_dir)
        self._artifacts: dict[str, BaseModel] = {}
        # _lookup memorizza il risultato autorevole del backend prima che l'agente
        # lo pubblichi. _validation accumula i tentativi, inclusi quelli rifiutati.
        self._lookup: VulnerabilityReport | None = None
        self._validation = SemanticValidationReport(validations=[])
        self._commit("input", self.case)

    def _commit(self, name: str, value: T) -> T:
        # Pubblicazione idempotente: ripetere gli stessi dati è consentito, cambiarli
        # dopo la prima scrittura no. Questo permette retry senza riscrivere le evidenze.
        if name in self._artifacts:
            if self._artifacts[name] != value:
                raise ValueError(f"Artifact {name} is immutable once published")
            return value
        path = self.output_dir / f"{name}.json"
        with path.open("x", encoding="utf-8") as stream:
            stream.write(value.model_dump_json(indent=2) + "\n")
        # Non conserviamo l'oggetto del chiamante: una successiva modifica a liste
        # o campi annidati non deve cambiare retroattivamente ciò che è stato pubblicato.
        self._artifacts[name] = value.model_copy(deep=True)
        return value

    def require(self, name: str, schema: type[T]) -> T:
        # Un prerequisito mancante è un errore, non un valore predefinito inventato.
        # La ricostruzione tramite model_validate restituisce una copia tipizzata
        # e riesegue i controlli dello schema anche sui dati già presenti in memoria.
        if name not in self._artifacts:
            raise ValueError(f"Missing prerequisite artifact: {name}")
        return schema.model_validate(self._artifacts[name].model_dump())

    def get_context(self) -> dict:
        """Read authoritative input, validated artifacts, and required JSON schemas.

        Returns:
            dict: Separate artifacts and their producers. StrategicAgent must read
                runtime_evidence, vulnerability_report and candidate_strategies individually.
        """
        # Ogni artefatto rimane sotto la propria chiave. model_dump produce dati
        # serializzabili separati dai modelli interni; i consumatori non ricevono
        # riferimenti mutabili allo stato. Sono esposti solo produttori già pubblicati.
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
        # Tre letture distinte mantengono l'evidenza di TelemetryAgent indipendente
        # dal rapporto e dalle strategie, anche se queste sono già state generate.
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
        # Pydantic controlla struttura e tipi; questo confronto aggiunge il controllo
        # semantico minimo: il modello non può alterare software/versione o fatti booleani.
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

        Call with the empty arguments object {}. This tool accepts no arguments;
        software and version are read from the published RuntimeEvidence.

        Returns:
            dict: Authoritative VulnerabilityReport, ready to publish unchanged.
        """
        evidence = self.require("runtime_evidence", RuntimeEvidence)
        if self._lookup is None:
            # Nel primo MVP c'è una sola osservazione software. Il lookup riceve
            # quella pubblicata, non un nome di pacchetto proposto liberamente dall'LLM.
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
        # Il confronto con la cache impedisce all'agente di inventare CVE o cambiare
        # CVSS/confidenza. La pubblicazione crea un report autonomo; non tocca evidence.
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
        # Le strategie devono riferirsi a CVE note. Con lookup non supportato si
        # richiede un set vuoto: non si scambia la mancanza di dati per una diagnosi.
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
        # Il tool proietta le candidate nel grafo; non modifica le loro stime e non
        # calcola la classifica. Gli altri due input devono comunque essere disponibili.
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
        # Oltre alla validità del modello, il risultato deve riferirsi esattamente
        # al grafo e alle strategie di questo run, anche con un backend sostitutivo.
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
        if not ranking.ranking:
            raise ValueError(
                "Ranking is empty: do not call validate_countermeasure. "
                "Call publish_final_decision with selected_strategy_id=null and an "
                "explanation; it also publishes the empty semantic_validation report. "
                "Then call record_provenance."
            )
        for previous in self._validation.validations:
            # Un retry restituisce la validazione già ottenuta senza aggiungere
            # un secondo tentativo né richiamare il backend per la stessa strategia.
            if previous.strategy_id == strategy_id:
                return previous.model_dump(mode="json")
        if any(v.valid for v in self._validation.validations):
            raise ValueError("The first accepted candidate has already been found")
        index = len(self._validation.validations)
        # Il numero di tentativi identifica il prossimo candidato: non è ammesso
        # saltare il primo classificato o continuare dopo un candidato accettato.
        if index >= len(ranking.ranking) or ranking.ranking[index].strategy_id != strategy_id:
            raise ValueError("Validate strategies in ranking order without skipping candidates")
        candidates = self.require("candidate_strategies", CandidateStrategies)
        strategy = next(s for s in candidates.strategies if s.id == strategy_id)
        context = DecisionContext(
            # Il validatore riceve la strategia separata dal contesto, che include
            # evidence, report e capacità/policy del caso; non riceve un riassunto LLM.
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
        # Questo è l'unico report aggiornato progressivamente. La scrittura su un
        # temporaneo seguita da replace evita di esporre un JSON scritto solo a metà.
        temporary.write_text(self._validation.model_dump_json(indent=2) + "\n", encoding="utf-8")
        temporary.replace(path)
        self._artifacts["semantic_validation"] = self._validation.model_copy(deep=True)
        return result.model_dump(mode="json")

    def publish_final_decision(self, selected_strategy_id: str | None, explanation: str) -> dict:
        """Publish a decision consistent with the ranking and all validation attempts.

        With an empty ranking, call this directly with selected_strategy_id=null,
        without calling validate_countermeasure. This also publishes the empty
        semantic_validation report. Call record_provenance after success.

        Args:
            selected_strategy_id (str | None): First accepted strategy, or null if none.
            explanation (str): Agent commentary, preserved as unverified. The tool builds
                the authoritative explanation and source references from validated artifacts.

        Returns:
            dict: FinalDecision. Scores and validation are copied from backend artifacts.
        """
        ranking = self.require("ranking", RankingResult)
        evidence, report, candidates = self._require_strategic_inputs()
        # Una validazione positiva da sola non basta: la decisione deve continuare
        # a riferirsi alle candidate pubblicate e a entrambi gli artefatti di origine.
        if {r.strategy_id for r in ranking.ranking} != {s.id for s in candidates.strategies}:
            raise ValueError("Final decision ranking must match the published candidate strategies")
        accepted = next((v for v in self._validation.validations if v.valid), None)
        # Lo StrategicAgent fornisce ID e spiegazione, ma non può imporre score,
        # ranking o esito semantico: questi valori vengono copiati dai risultati dei tool.
        expected_id = accepted.strategy_id if accepted else None
        if selected_strategy_id != expected_id:
            raise ValueError("Select exactly the first semantically accepted strategy")
        if accepted is None and len(self._validation.validations) != len(ranking.ranking):
            raise ValueError("Validate every ranked strategy before declaring none acceptable")
        if "semantic_validation" not in self._artifacts:
            # Anche un ranking vuoto produce un report di validazione vuoto,
            # mantenendo completo e uniforme l'insieme degli otto artefatti.
            self._commit("semantic_validation", self._validation)
        status = "selected" if accepted else "no_valid_strategy"
        if report.lookup_status == "unsupported":
            # «Nessuna strategia valida» e «dati insufficienti» sono esiti diversi.
            status = "insufficient_evidence"
        claims = self._decision_claims(expected_id)
        decision = FinalDecision(
            status=status,
            selected_strategy_id=expected_id,
            ranking=ranking.ranking,
            semantic_validation=accepted,
            evidence_ids=[s.evidence_id for s in evidence.software],
            explanation="\n\n".join(c.text for c in claims),
            explanation_method="artifact-derived-v1",
            explanation_claims=claims,
            agent_commentary=AgentCommentary(text=explanation),
        )
        return self._commit("final_decision", decision).model_dump(mode="json")

    def _decision_claims(self, selected_strategy_id: str | None):
        evidence, report, candidates = self._require_strategic_inputs()
        producers = {
            **ARTIFACT_PRODUCERS,
            "ranking": "StrategicAgent",
            "semantic_validation": "StrategicAgent",
        }
        if self.mode == "fixtures":
            producers = {name: f"fixture:{producer}" for name, producer in producers.items()}
        producers["input"] = "StaticTelemetry"
        return build_explanation(
            self.case,
            evidence,
            report,
            candidates,
            self.require("ranking", RankingResult),
            self.require("semantic_validation", SemanticValidationReport),
            selected_strategy_id,
            producers,
        )

    def record_provenance(self) -> dict:
        """Record input/output hashes and the agents responsible for each activity.

        Returns:
            dict: Local provenance receipt. Must be called after publishing the decision.
        """
        self.require("final_decision", FinalDecision)
        if "provenance" in self._artifacts:
            return {"run_id": self.run_id, "stored": True}
        stages = [
            # Proiezione dichiarativa delle dipendenze di dominio. Non è un log
            # di tutte le chiamate LLM o dei retry; collega used/generated ai file.
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
                    "input",
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
            # L'hash riguarda i byte realmente salvati, inclusi indentazione e newline.
            # Serve a confrontare i contenuti, ma non costituisce una firma digitale.
            ProvenanceEntity(
                id=name,
                filename=f"{name}.json",
                sha256=hashlib.sha256((self.output_dir / f"{name}.json").read_bytes()).hexdigest(),
            )
            for name in self._artifacts
        ]
        record = ProvenanceRecord(
            # La modalità fixtures rende esplicito che i produttori erano dati di
            # prova; evita di attribuire a un LLM output che non ha generato.
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
        # Un futuro backend potrebbe persistere altrove: la sessione conserva
        # comunque una copia locale, verificando quella eventualmente già scritta.
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
        # Controllo finale su presenza, schema e corrispondenza memoria/file. Non
        # basta che il task CAMEL termini con DONE o che esista final_decision.json.
        for name, schema in ARTIFACT_SCHEMAS.items():
            value = self.require(name, schema)
            stored = schema.model_validate_json((self.output_dir / f"{name}.json").read_text())
            if value != stored:
                raise ValueError(f"Stored artifact differs from validated state: {name}")
        decision = self.require("final_decision", FinalDecision)
        # Ricostruisce la spiegazione dalle fonti: non basta che riferimenti e
        # testo abbiano la forma corretta o che file e memoria coincidano.
        if decision.explanation_method != "artifact-derived-v1" or (
            decision.explanation_claims != self._decision_claims(decision.selected_strategy_id)
        ):
            raise ValueError("Final explanation must be derived from the current artifacts")
        return decision


def json_payload(value: BaseModel | dict) -> str:
    # Uniforma la preparazione dei payload per i tool: modelli Pydantic o dizionari
    # diventano una stringa JSON, poi nuovamente validata al confine di pubblicazione.
    return value.model_dump_json() if isinstance(value, BaseModel) else json.dumps(value)
