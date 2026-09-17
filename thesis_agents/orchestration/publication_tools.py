"""Adatta gli argomenti strutturati CAMEL alle pubblicazioni della sessione.

L'LLM fornisce un oggetto JSON, non una stringa contenente un secondo JSON.
CAMEL ricava lo schema dai modelli Pydantic; la sessione conserva tutti i suoi
controlli e l'API JSON già usata dalle fixture e dagli altri chiamanti Python.
"""

from camel.toolkits import FunctionTool
from camel.toolkits.function_tool import get_openai_tool_schema

from thesis_agents.orchestration.artifacts import ArtifactSession
from thesis_agents.schemas import CandidateStrategies, RuntimeEvidence, VulnerabilityReport


class PublicationTools:
    def __init__(self, session: ArtifactSession):
        self.session = session

    def publish_runtime_evidence(self, payload: RuntimeEvidence) -> dict:
        """Publish runtime evidence preserving the observed input facts.

        Args:
            payload (RuntimeEvidence): Evidence as a JSON object, never a quoted JSON string.

        Returns:
            dict: Validated runtime evidence, saved by ArtifactSession.
        """
        evidence = RuntimeEvidence.model_validate(payload)
        return self.session.publish_runtime_evidence(evidence.model_dump_json())

    def publish_vulnerability_report(self, payload: VulnerabilityReport) -> dict:
        """Publish the exact report returned by lookup_vulnerabilities.

        Args:
            payload (VulnerabilityReport): Lookup report as a JSON object, not a JSON string.

        Returns:
            dict: Validated vulnerability report, saved by ArtifactSession.
        """
        report = VulnerabilityReport.model_validate(payload)
        return self.session.publish_vulnerability_report(report.model_dump_json())

    def publish_candidate_strategies(self, payload: CandidateStrategies) -> dict:
        """Publish generated strategies grounded in the separate evidence and report.

        Args:
            payload (CandidateStrategies): Strategies as a JSON object, not a JSON string.

        Returns:
            dict: Validated candidate strategies, saved by ArtifactSession.
        """
        candidates = CandidateStrategies.model_validate(payload)
        return self.session.publish_candidate_strategies(candidates.model_dump_json())

    def resolve(self, name: str):
        # Solo le tre pubblicazioni richiedono un adapter. Gli altri tool restano
        # i metodi originali della medesima sessione, inclusa get_context.
        if name in (
            "publish_runtime_evidence",
            "publish_vulnerability_report",
            "publish_candidate_strategies",
        ):
            method = getattr(self, name)
            schema = get_openai_tool_schema(method)
            parameters = schema["function"]["parameters"]
            # Espone direttamente l'oggetto del payload. CAMEL 0.2.90 omette la
            # descrizione sui $ref; manteniamo i $defs per i modelli annidati.
            reference = parameters["properties"]["payload"]["$ref"]
            parameters["properties"]["payload"] = {
                **parameters["$defs"][reference.rsplit("/", 1)[-1]],
                "description": "Artifact as a JSON object, never a quoted JSON string.",
            }
            return FunctionTool(method, openai_tool_schema=schema)
        return getattr(self.session, name)
