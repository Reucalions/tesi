"""Adatta il riepilogo CAMEL ai contratti di pubblicazione del prototipo."""

from camel.societies.workforce.structured_output_handler import StructuredOutputHandler

from thesis_agents.orchestration.artifacts import ARTIFACT_SCHEMAS, ArtifactSession


class ArtifactTaskHandler(StructuredOutputHandler):
    """Il testo del worker non basta a dimostrare che abbia pubblicato il risultato."""

    def __init__(self, session: ArtifactSession, outputs: tuple[str, ...]):
        self.session = session
        self.outputs = outputs

    def _missing_outputs(self):
        missing = []
        for name in self.outputs:
            try:
                self.session.require(name, ARTIFACT_SCHEMAS[name])
            except ValueError:
                missing.append(name)
        return missing

    def generate_structured_prompt(
        self, base_prompt, schema, examples=None, additional_instructions=None
    ):
        # CAMEL 0.2.90 antepone al task esempi di risposte senza tool. Conserviamo
        # task, parent e dipendenze, rimuovendo solo quel preambolo di formattazione.
        # Il marker fa parte di PROCESS_TASK_PROMPT nell'SDK fissato nel progetto.
        marker = "Here is the content of the task that you need to do:\n"
        _, found, task_context = base_prompt.partition(marker)
        if not found:
            raise RuntimeError("Unexpected CAMEL task prompt; check SDK compatibility")
        missing = self._missing_outputs()
        published = [name for name in self.outputs if name not in missing]
        return (
            "Execute the following task using your tools.\n"
            + marker
            + task_context
            + "\nCall get_context with arguments {} and read the returned input. "
            "Execute your role's tools to publish the following artifacts: "
            + ", ".join(self.outputs)
            + ".\nAlready published artifacts: "
            + (", ".join(published) or "none")
            + ".\nRemaining artifacts: "
            + (", ".join(missing) or "none")
            + ". Read get_context to reuse the validated results already available; "
            "do not regenerate or replace them. Complete the remaining tool calls. "
            "A tool call is necessary for every publication. "
            "After successful publication, end with a JSON object containing "
            "content (a short summary) and failed (false). "
            "If a tool fails, correct the call or report failed=true."
        )

    def parse_structured_response(self, response_text, schema, fallback_values=None):
        result = super().parse_structured_response(response_text, schema, fallback_values)
        # Il controllo avviene prima che SingleAgentWorker comunichi DONE a CAMEL.
        # Non creiamo artefatti per conto del modello e non correggiamo i suoi dati.
        missing = self._missing_outputs()
        if missing:
            return schema(
                content="Publication contract failed. Remaining artifacts: " + ", ".join(missing),
                failed=True,
            )
        return result
