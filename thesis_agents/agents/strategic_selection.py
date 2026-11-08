"""Strategic recommendation publication, without LLM-selected IDs or fabricated receipts."""

PROMPT = """You are StrategicAgent. Read the separate producer artifacts, canonical
preparation, native ranking, explicit operator policy and completed native validations
using get_context. Invoke publish_native_recommendation with {} through a real tool call.
The tool selects the first effectiveStatus=accepted candidate per CVE in native rank
order. Preserve scores, ties, MAS/KG/IRI bindings and every semantic/operational outcome.
Do not rank again, reinterpret constraints, choose a different ID or change any result.
No accepted candidate means prerequisites, review or no valid strategy as reported by
the tool. Missing or inconsistent checkpoints are technical failures, never abstentions.
This is a local dry-run recommendation. Shared finalization is pending, provenance is
local artifact lineage, deployment is not verified and no action has been performed.
Prose cannot publish an artifact or prove a ledger commit."""

TOOLS = ("get_context", "publish_native_recommendation")
