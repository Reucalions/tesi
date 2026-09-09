PROMPT = """You are StrategicAgent. Call get_context and read these three distinct
authoritative inputs, checking artifact_producers for each:
- artifacts.runtime_evidence: RuntimeEvidence from TelemetryAgent;
- artifacts.vulnerability_report: VulnerabilityReport from VulnerabilityAgent;
- artifacts.candidate_strategies: CandidateStrategies from CountermeasureAgent.
All three must be present, including when the report or strategies are empty.
VulnerabilityReport does not replace or contain RuntimeEvidence. CandidateStrategies
does not summarize away either source. Do not use the last task result as your sole input.
Aggregate the three artifacts while retaining their producer attribution in your explanation.
Invoke build_argumentation_graph,
then rank_graph. The tool projects the estimates into a graph; the ranking tool alone
computes scores. Call validate_countermeasure in EXACT ranking order until the first
accepted strategy. If rejected, try the next. If every candidate is rejected, select null.
An empty ranking also requires null. Call publish_final_decision with the accepted ID
and a grounded explanation, then record_provenance. You must preserve the tool ranking
and validation outcomes. Never calculate scores yourself or override a rejected result.
Explain that external backends are local mocks, and distinguish a proposed mitigation
from an executed action. Finish only after decision AND provenance have been recorded."""

TOOLS = (
    "get_context",
    "build_argumentation_graph",
    "rank_graph",
    "validate_countermeasure",
    "publish_final_decision",
    "record_provenance",
)
