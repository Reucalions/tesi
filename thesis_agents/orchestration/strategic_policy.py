"""Disponibilità dei tool derivata dagli artefatti, senza eseguire il dominio.

Ogni clone deve leggere il contesto. Le fasi successive dipendono solo da
pubblicazioni riuscite: testo LLM ed errori dei tool non fanno avanzare lo stato.
"""

from camel.terminators import ResponseTerminator

from thesis_agents.schemas import RankingResult, SemanticValidationReport


class StrategicToolPolicy(ResponseTerminator):
    def __init__(self, session):
        super().__init__()
        self.session = session
        self.reset()

    def reset(self):
        self.context_read = False
        self.premature_responses = 0

    def clone(self):
        return type(self)(self.session)

    def next_tool(self):
        if not self.context_read:
            return "get_context"
        artifacts = self.session.get_context()["artifacts"]
        for artifact, tool in (
            ("argumentation_graph", "build_argumentation_graph"),
            ("ranking", "rank_graph"),
        ):
            if artifact not in artifacts:
                return tool
        if "final_decision" not in artifacts:
            ranking = self.session.require("ranking", RankingResult).ranking
            validations = (
                self.session.require("semantic_validation", SemanticValidationReport).validations
                if "semantic_validation" in artifacts
                else []
            )
            if not any(v.valid for v in validations) and len(validations) < len(ranking):
                return "validate_countermeasure"
            return "publish_final_decision"
        if "provenance" not in artifacts:
            return "record_provenance"
        return None

    def observe(self, name, result):
        if isinstance(result, dict):
            if name == "get_context":
                required = {"runtime_evidence", "vulnerability_report", "candidate_strategies"}
                self.context_read = required <= result.get("artifacts", {}).keys()
            self.premature_responses = 0

    def instruction(self):
        tool = self.next_tool()
        if tool is None:
            return "All required artifacts are published. Return the final TaskResult JSON."
        return (
            f"Current required tool: {tool}. Make a real structured tool call. "
            "No other tool is currently available. A JSON tool name in response text "
            "does not execute it. Use the evidence and tool results already in this conversation."
        )

    def is_terminated(self, messages):
        if self.next_tool() is None:
            return True, "All strategic artifacts published"
        # Un solo recupero in-sessione per una risposta testuale prematura.
        # Alla seconda il normale ArtifactTaskHandler respinge l'incompletezza.
        self.premature_responses += 1
        return self.premature_responses >= 2, "Required strategic publications still missing"
