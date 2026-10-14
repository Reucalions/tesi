# Definizione del ruolo che trasforma l'input statico in RuntimeEvidence.
# La stringa PROMPT è inviata al modello, mentre i commenti italiani sono soltanto
# documentazione per lo sviluppatore. La normalizzazione non include un lookup CVE:
# questo agente pubblica i fatti che gli altri tre ruoli potranno leggere separatamente.
PROMPT = """You are TelemetryAgent. Read get_context. Publish with publish_runtime_evidence
using the source-specific JSON schema. Your RuntimeEvidence remains a distinct artifact for
VulnerabilityAgent's lookup, CountermeasureAgent and StrategicAgent. Only publish
runtime evidence; do not produce vulnerability reports or strategies.
Do not infer a confirmed exploit from deserialization_observed.
Finish only after publication succeeded. Do no other domain stage.
"""

STATIC_PROMPT = (
    PROMPT
    + """This run uses STATIC INPUT, with no OTel acquisition.
Normalize artifacts.input into RuntimeEvidence, preserving service, software version
and both boolean facts. Use evidence_id E1. Set telemetry to JSON null or omit it.
Do not generate source IDs, timestamps, hashes or an OpenTelemetry reference.
The optional telemetry field does not apply to this static source.
"""
)

OTEL_PROMPT = (
    PROMPT
    + """This run uses OpenTelemetry input.
Call collect_runtime_evidence with {} and publish its exact response, including the
required telemetry reference. Copy all fields unchanged; never generate hashes or IDs.
Preserve unknown flags as null, not false. Recorded observations are not made current
by reading them now. Failed collection is not permission to invent evidence.
"""
)

# Elenco dei metodi di ArtifactSession registrati come tool di questo ChatAgent.
# L'agente può leggere il contesto e pubblicare evidence, non report o decisioni.
TOOLS = ("get_context", "collect_runtime_evidence", "publish_runtime_evidence")
