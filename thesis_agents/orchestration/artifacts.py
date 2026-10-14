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
from thesis_agents.schemas.decision import AgentCommentary, ExplanationClaim, ExplanationSource
from thesis_agents.schemas.provenance import ProvenanceActivity, ProvenanceEntity
from thesis_agents.schemas.supply_chain import (
    CountermeasureContext,
    SupplyChainQuery,
    SupplyChainSnapshot,
    countermeasure_context,
)
from thesis_agents.schemas.telemetry import runtime_publication_schema
from thesis_agents.schemas.telemetry_source import TelemetryInput, TelemetrySnapshot
from thesis_agents.tools.interfaces import (
    ProvenanceTool,
    RankingTool,
    SemanticTool,
    SupplyChainTool,
    TelemetryTool,
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
        case: StaticTelemetry | TelemetryInput,
        output_dir: Path,
        *,
        mode: str = "camel",
        model: str | None = None,
        telemetry_tool: TelemetryTool | None = None,
        supply_chain_tool: SupplyChainTool | None = None,
        vulnerability_tool: VulnerabilityTool | None = None,
        ranking_tool: RankingTool | None = None,
        semantic_tool: SemanticTool | None = None,
        provenance_tool: ProvenanceTool | None = None,
    ):
        # Una directory non vuota potrebbe contenere risultati di un altro run:
        # si rifiuta il riuso, così non si mescolano evidenze e decisioni precedenti.
        if mode not in ("camel", "fixtures"):
            raise ValueError("Unknown execution mode")
        if mode == "fixtures" and isinstance(case, TelemetryInput):
            raise ValueError("Fixtures require StaticTelemetry and no remote acquisition")
        if mode == "fixtures" and supply_chain_tool is not None:
            raise ValueError("Fixtures do not allow remote supply chain acquisition")
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
        self.telemetry_tool = telemetry_tool
        self.supply_chain_tool = supply_chain_tool
        self._supply_chain_snapshot: SupplyChainSnapshot | None = None
        self._countermeasure_context: CountermeasureContext | None = None
        self._telemetry_snapshot: TelemetrySnapshot | None = None
        self._telemetry_evidence: RuntimeEvidence | None = None
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
        self._provenance_receipt: dict | None = None
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
        context = {
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
        # Lo schema esposto per la pubblicazione dipende dalla fonte. I dati
        # salvati e letti dagli altri agenti restano nello schema RuntimeEvidence.
        context["schemas"]["runtime_evidence"] = runtime_publication_schema(
            self.case
        ).model_json_schema()
        if self.supply_chain_tool is not None:
            if self._countermeasure_context is not None:
                self._verify_supply_chain_snapshot()
            context["external_inputs"] = {
                "countermeasure": {
                    "required": True,
                    "producer": "ArtifactSession.collect_countermeasure_context",
                    "context": self._countermeasure_context.model_dump(mode="json")
                    if self._countermeasure_context is not None
                    else None,
                }
            }
        return context

    def _require_strategic_inputs(
        self,
    ) -> tuple[RuntimeEvidence, VulnerabilityReport, CandidateStrategies]:
        """Validate each producer's artifact independently, never a chain summary."""
        # Tre letture distinte mantengono l'evidenza di TelemetryAgent indipendente
        # dal rapporto e dalle strategie, anche se queste sono già state generate.
        self._verify_supply_chain_snapshot()
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
        if isinstance(self.case, TelemetryInput):
            if self._telemetry_evidence is None or evidence != self._telemetry_evidence:
                raise ValueError("Call collect_runtime_evidence and preserve its exact evidence")
            self._verify_telemetry_snapshot()
            return self._commit("runtime_evidence", evidence).model_dump(mode="json")
        # Pydantic controlla struttura e tipi; questo confronto aggiunge il controllo
        # semantico minimo: il modello non può alterare software/versione o fatti booleani.
        case = self.case
        if (
            evidence.service_name != case.service_name
            or evidence.telemetry is not None
            or evidence.endpoint_exposed != case.endpoint_exposed
            or evidence.deserialization_observed != case.deserialization_observed
            or len(evidence.software) != 1
            or evidence.software[0].package != case.package_name
            or evidence.software[0].version != case.package_version
        ):
            raise ValueError("RuntimeEvidence must preserve the static telemetry facts")
        return self._commit("runtime_evidence", evidence).model_dump(mode="json")

    def collect_runtime_evidence(self) -> dict:
        """Read configured OTEL observations and return evidence ready to publish.

        Call with {} only when input.source is opentelemetry. The input fixes
        source selector, service instance, package and time window. Unknown flags
        stay null. No observations or ambiguous versions raise an error.

        Returns:
            dict: Authoritative RuntimeEvidence, to publish unchanged.
        """
        if not isinstance(self.case, TelemetryInput) or self.telemetry_tool is None:
            raise ValueError("OpenTelemetry input and a configured telemetry tool are required")
        from thesis_agents.tools.telemetry_http import evidence_from_snapshot

        if self._telemetry_snapshot is None:
            snapshot = self.telemetry_tool.collect(self.case.query())
            if snapshot.query != self.case.query():
                raise ValueError("Telemetry snapshot selector differs from input")
            with (self.output_dir / "telemetry_snapshot.json").open(
                "x", encoding="utf-8"
            ) as stream:
                stream.write(snapshot.model_dump_json(indent=2) + "\n")
            self._telemetry_snapshot = snapshot.model_copy(deep=True)
        # Una query vuota/ambigua conserva lo snapshot per diagnosi, senza pubblicare.
        self._telemetry_evidence = evidence_from_snapshot(self._telemetry_snapshot)
        self._verify_telemetry_snapshot()
        return self._telemetry_evidence.model_dump(mode="json")

    def _verify_telemetry_snapshot(self):
        if not isinstance(self.case, TelemetryInput):
            return
        from thesis_agents.tools.telemetry_http import evidence_from_snapshot

        stored = TelemetrySnapshot.model_validate_json(
            (self.output_dir / "telemetry_snapshot.json").read_text(encoding="utf-8")
        )
        if (
            stored != self._telemetry_snapshot
            or stored.query != self.case.query()
            or evidence_from_snapshot(stored) != self._telemetry_evidence
        ):
            raise ValueError("Telemetry snapshot differs from validated source evidence")

    def lookup_vulnerabilities(self) -> dict:
        """Query the vulnerability backend for the published software observation.

        Call with the empty arguments object {}. This tool accepts no arguments;
        software and version are read from the published RuntimeEvidence.

        Returns:
            dict: Authoritative VulnerabilityReport, ready to publish unchanged.
        """
        evidence = self.require("runtime_evidence", RuntimeEvidence)
        self._verify_telemetry_snapshot()
        if self._lookup is None:
            # Nel primo MVP c'è una sola osservazione software. Il lookup riceve
            # quella pubblicata, non un nome di pacchetto proposto liberamente dall'LLM.
            result = self.vulnerability_tool.lookup_vulnerabilities(evidence.software[0])
            self._lookup = VulnerabilityReport(
                asset_id=evidence.service_name,
                lookup_status=result.status,
                vulnerabilities=result.vulnerabilities,
                cti=result.cti,
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
        self._verify_cti_snapshot(report)
        return self._commit("vulnerability_report", report).model_dump(mode="json")

    def _verify_cti_snapshot(self, report):
        """La sintesi pubblicata deve restare derivabile dallo snapshot MCP salvato."""
        if report.cti is None:
            return
        from thesis_agents.mcp.client import digest
        from thesis_agents.mcp.cti_contracts import AssessmentResponse
        from thesis_agents.tools.cti_mcp import map_assessment

        software = self.require("runtime_evidence", RuntimeEvidence).software[0]
        response = AssessmentResponse.model_validate_json(
            (self.output_dir / "cti_assessment.json").read_text(encoding="utf-8")
        )
        if digest(response.model_dump(mode="json")) != report.cti.response_sha256:
            raise ValueError("Lo snapshot CTI è cambiato dopo il lookup")
        mapped = map_assessment(response, software)
        if (mapped.status, mapped.vulnerabilities, mapped.cti) != (
            report.lookup_status,
            report.vulnerabilities,
            report.cti,
        ):
            raise ValueError("Report non derivato dallo snapshot CTI e dall'evidenza runtime")

    def publish_candidate_strategies(self, payload: str) -> dict:
        """Validate and publish strategies generated by the CountermeasureAgent.

        Args:
            payload (str): JSON matching candidate_strategies from get_context.

        Returns:
            dict: Validated CandidateStrategies with unique IDs and known CVEs.
        """
        self.require("runtime_evidence", RuntimeEvidence)
        report = self.require("vulnerability_report", VulnerabilityReport)
        self._verify_supply_chain_snapshot()
        candidates = CandidateStrategies.model_validate_json(payload)
        known = {v.cve_id for v in report.vulnerabilities}
        # Le strategie devono riferirsi a CVE note. Con lookup non supportato si
        # richiede un set vuoto: non si scambia la mancanza di dati per una diagnosi.
        if known and not candidates.strategies:
            raise ValueError("Generate at least one strategy for the known vulnerability")
        if not known and candidates.strategies:
            raise ValueError(
                "A lookup without confirmed findings cannot ground remediation strategies"
            )
        for strategy in candidates.strategies:
            if not set(strategy.addressed_vulnerabilities) <= known:
                raise ValueError("Candidate references an unknown vulnerability")
        return self._commit("candidate_strategies", candidates).model_dump(mode="json")

    def collect_countermeasure_context(self) -> dict:
        """Acquire configured SBOM/OSV data for the published runtime observation.

        Call with {} after runtime_evidence and vulnerability_report are published,
        when external_inputs.countermeasure.required is true. Read get_context again
        before generating candidates. This never changes the authoritative CTI report.

        Returns:
            dict: Validated supporting context; fixed range events are not safe targets.
        """
        if self.supply_chain_tool is None or self.mode == "fixtures":
            raise ValueError("A configured remote supply chain input is required")
        evidence = self.require("runtime_evidence", RuntimeEvidence)
        report = self.require("vulnerability_report", VulnerabilityReport)
        self._verify_telemetry_snapshot()
        self._verify_cti_snapshot(report)
        query = SupplyChainQuery(service_name=evidence.service_name, software=evidence.software[0])
        if self._supply_chain_snapshot is None:
            snapshot = SupplyChainSnapshot.model_validate(
                self.supply_chain_tool.collect(query).model_dump(mode="json")
            )
            if snapshot.query != query:
                raise ValueError("Supply chain query differs from runtime evidence")
            with (self.output_dir / "supply_chain_snapshot.json").open(
                "x", encoding="utf-8"
            ) as stream:
                stream.write(snapshot.model_dump_json(indent=2) + "\n")
            self._supply_chain_snapshot = snapshot.model_copy(deep=True)
        if self._countermeasure_context is None:
            context = countermeasure_context(self._supply_chain_snapshot, report)
            with (self.output_dir / "countermeasure_context.json").open(
                "x", encoding="utf-8"
            ) as stream:
                stream.write(context.model_dump_json(indent=2) + "\n")
            self._countermeasure_context = context.model_copy(deep=True)
        self._verify_supply_chain_snapshot()
        return self._countermeasure_context.model_dump(mode="json")

    def _verify_supply_chain_snapshot(self):
        if self.supply_chain_tool is None:
            return
        if self._countermeasure_context is None or self._supply_chain_snapshot is None:
            raise ValueError("Call collect_countermeasure_context before publishing strategies")
        evidence = self.require("runtime_evidence", RuntimeEvidence)
        report = self.require("vulnerability_report", VulnerabilityReport)
        stored = SupplyChainSnapshot.model_validate_json(
            (self.output_dir / "supply_chain_snapshot.json").read_text(encoding="utf-8")
        )
        context = CountermeasureContext.model_validate_json(
            (self.output_dir / "countermeasure_context.json").read_text(encoding="utf-8")
        )
        if (
            stored != self._supply_chain_snapshot
            or stored.query
            != SupplyChainQuery(service_name=evidence.service_name, software=evidence.software[0])
            or context != self._countermeasure_context
            or context != countermeasure_context(stored, report)
        ):
            raise ValueError("Supply chain snapshot/context differs from validated evidence")

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
        self._verify_telemetry_snapshot()
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
        if report.lookup_status in ("unsupported", "ambiguous", "no_match", "not_evaluable"):
            # «Nessuna strategia valida» e «dati insufficienti» sono esiti diversi.
            status = "insufficient_evidence"
        elif report.lookup_status == "no_findings":
            status = "no_findings"
        self._verify_cti_snapshot(report)
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
        producers["input"] = (
            "TelemetryInput" if isinstance(self.case, TelemetryInput) else "StaticTelemetry"
        )
        claims = build_explanation(
            self.case,
            evidence,
            report,
            candidates,
            self.require("ranking", RankingResult),
            self.require("semantic_validation", SemanticValidationReport),
            selected_strategy_id,
            producers,
        )
        if self._countermeasure_context is not None:
            context = self._countermeasure_context
            claims.append(
                ExplanationClaim(
                    category="limitation",
                    text=(
                        f"Countermeasure input uses SBOM kind={context.sbom_kind} and "
                        f"OSV kind={context.osv_kind}; {len(context.advisories)} active advisories "
                        "correlate with existing CTI findings. "
                        "SBOM binding is declared, not attested. "
                        "OSV fixed boundaries do not establish a globally safe "
                        "or compatible upgrade; "
                        "OSV-only advisories do not become confirmed CTI findings."
                    ),
                    sources=[
                        ExplanationSource(
                            artifact="countermeasure_context",
                            pointer=pointer,
                            producer="ArtifactSession.collect_countermeasure_context",
                        )
                        for pointer in ("/sbom_kind", "/osv_kind", "/advisories", "/limitations")
                    ],
                )
            )
        return claims

    def record_provenance(self) -> dict:
        """Record input/output hashes and the agents responsible for each activity.

        Returns:
            dict: Configured backend receipt. Must follow publication of the decision.
        """
        self.require("final_decision", FinalDecision)
        self._verify_supply_chain_snapshot()
        if "provenance" in self._artifacts:
            # Un retry restituisce anche l'identità/digest della ricevuta remota,
            # senza ripetere una scrittura di cui abbiamo già conferma.
            return dict(self._provenance_receipt)
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
        report = self.require("vulnerability_report", VulnerabilityReport)
        if isinstance(self.case, TelemetryInput):
            self._verify_telemetry_snapshot()
            entities.append(
                ProvenanceEntity(
                    id="telemetry_snapshot",
                    filename="telemetry_snapshot.json",
                    sha256=hashlib.sha256(
                        (self.output_dir / "telemetry_snapshot.json").read_bytes()
                    ).hexdigest(),
                )
            )
            stages.insert(0, ("collect", "TelemetryAgent", ["input"], ["telemetry_snapshot"]))
            next(stage for stage in stages if stage[0] == "telemetry")[2].append(
                "telemetry_snapshot"
            )
        if report.cti is not None:
            self._verify_cti_snapshot(report)
            entities.append(
                ProvenanceEntity(
                    id="cti_assessment",
                    filename="cti_assessment.json",
                    sha256=hashlib.sha256(
                        (self.output_dir / "cti_assessment.json").read_bytes()
                    ).hexdigest(),
                )
            )
            stages.insert(
                next(i for i, stage in enumerate(stages) if stage[0] == "lookup"),
                ("remote_lookup", "VulnerabilityAgent", ["runtime_evidence"], ["cti_assessment"]),
            )
            next(stage for stage in stages if stage[0] == "lookup")[2].append("cti_assessment")
        if self.supply_chain_tool is not None:
            for name in ("supply_chain_snapshot", "countermeasure_context"):
                entities.append(
                    ProvenanceEntity(
                        id=name,
                        filename=f"{name}.json",
                        sha256=hashlib.sha256(
                            (self.output_dir / f"{name}.json").read_bytes()
                        ).hexdigest(),
                    )
                )
            offset = next(i for i, stage in enumerate(stages) if stage[0] == "candidates")
            stages[offset:offset] = [
                (
                    "supply_chain_lookup",
                    "CountermeasureAgent",
                    ["runtime_evidence"],
                    ["supply_chain_snapshot"],
                ),
                (
                    "supply_chain_context",
                    "CountermeasureAgent",
                    ["supply_chain_snapshot", "vulnerability_report"],
                    ["countermeasure_context"],
                ),
            ]
            next(stage for stage in stages if stage[0] == "candidates")[2].append(
                "countermeasure_context"
            )
            next(stage for stage in stages if stage[0] == "decision")[2].append(
                "countermeasure_context"
            )
        record = ProvenanceRecord(
            # La modalità fixtures rende esplicito che i produttori erano dati di
            # prova; evita di attribuire a un LLM output che non ha generato.
            run_id=self.run_id,
            mode=self.mode,
            model=self.model,
            backend=getattr(self.provenance_tool, "backend", "local-provenance-mock-v1"),
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
        self._provenance_receipt = dict(receipt)
        return receipt

    def assert_complete(self) -> FinalDecision:
        # Controllo finale su presenza, schema e corrispondenza memoria/file. Non
        # basta che il task CAMEL termini con DONE o che esista final_decision.json.
        self._verify_telemetry_snapshot()
        self._verify_supply_chain_snapshot()
        for name, schema in ARTIFACT_SCHEMAS.items():
            value = self.require(name, schema)
            stored = schema.model_validate_json((self.output_dir / f"{name}.json").read_text())
            if value != stored:
                raise ValueError(f"Stored artifact differs from validated state: {name}")
        self._verify_cti_snapshot(self.require("vulnerability_report", VulnerabilityReport))
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
