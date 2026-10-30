"""Fasi di pubblicazione Ubuntu: un tool per volta, nessun output creato dalla policy."""

from thesis_agents.orchestration.strategic_policy import StrategicToolPolicy


class CountermeasureToolPolicy(StrategicToolPolicy):
    def next_tool(self):
        if not self.context_read:
            return "get_context"
        context = self.session.get_context()
        external = context.get("external_inputs", {})
        for name, tool in (
            ("countermeasure", "collect_countermeasure_context"),
            ("package_verification", "prepare_package_verification"),
        ):
            source = external.get(name, {})
            if source.get("required") and source.get("context") is None:
                return tool
        if "candidate_strategies" not in context["artifacts"]:
            return "publish_candidate_strategies"
        return None

    def observe(self, name, result):
        if not isinstance(result, dict):
            return
        if name == "get_context":
            required = {"runtime_evidence", "vulnerability_report"}
            self.context_read = required <= result.get("artifacts", {}).keys()
        elif name in ("collect_countermeasure_context", "prepare_package_verification"):
            self.context_read = False
        self.premature_responses = 0

    def is_terminated(self, messages):
        if self.next_tool() is None:
            return True, "Countermeasure artifact published"
        self.premature_responses += 1
        return self.premature_responses >= 2, "Required countermeasure publication still missing"
