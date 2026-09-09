from thesis_agents.schemas import (
    CountermeasureCandidate,
    DecisionContext,
    SemanticValidationResult,
)

# Tool-owned requirements cannot be bypassed by an LLM omitting prerequisites.
REQUIRED_CAPABILITIES = {
    "upgrade": {"maintenance_window", "package_upgrade"},
    "isolate": {"network_isolation"},
    "block_deployment": {"deployment_control"},
    "monitor": {"monitoring"},
}


class MockSemanticTool:
    """Capability/policy checks only; does not implement Tiny-ME reasoning."""

    def validate_countermeasure(
        self, strategy: CountermeasureCandidate, context: DecisionContext
    ) -> SemanticValidationResult:
        required = REQUIRED_CAPABILITIES[strategy.action] | set(strategy.prerequisites)
        missing = sorted(required - set(context.available_capabilities))
        conflicts = []
        if strategy.action in context.prohibited_actions:
            conflicts.append(f"Action prohibited by scenario: {strategy.action}")
        known_cves = {v.cve_id for v in context.vulnerabilities.vulnerabilities}
        if not set(strategy.addressed_vulnerabilities) <= known_cves:
            conflicts.append("Strategy references a vulnerability absent from the report")
        valid = not missing and not conflicts
        return SemanticValidationResult(
            strategy_id=strategy.id,
            valid=valid,
            status="accepted" if valid else "rejected",
            missing_requirements=missing,
            conflicts=conflicts,
            explanation=(
                "Local fixture requirements satisfied; this is not a Tiny-ME proof."
                if valid
                else "Local fixture requirements or policy not satisfied."
            ),
            backend="capability-policy-mock-v1",
        )
