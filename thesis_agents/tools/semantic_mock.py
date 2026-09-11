# Validatore locale basato su capacità disponibili e policy esplicite.
# Non interpreta ontologie, descrizioni o constraints in linguaggio naturale;
# «accepted» significa soltanto che questi controlli limitati sono soddisfatti.
# Il modulo non implementa Tiny-ME e non esegue la contromisura proposta.
from thesis_agents.schemas import (
    CountermeasureCandidate,
    DecisionContext,
    SemanticValidationResult,
)

# Requisiti stabiliti dal tool: il modello non può aggirarli omettendo una capacità
# nella propria proposta. L'upgrade richiede anche una finestra di manutenzione.
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
        # Unione fra requisiti obbligatori della categoria e prerequisiti aggiuntivi
        # dichiarati dalla candidata. La differenza individua le capacità mancanti.
        required = REQUIRED_CAPABILITIES[strategy.action] | set(strategy.prerequisites)
        missing = sorted(required - set(context.available_capabilities))
        conflicts = []
        # Un'azione fattibile può essere vietata dalla policy del caso.
        if strategy.action in context.prohibited_actions:
            conflicts.append(f"Action prohibited by scenario: {strategy.action}")
        known_cves = {v.cve_id for v in context.vulnerabilities.vulnerabilities}
        # Il tool ricontrolla il legame con il report anche se la sessione valida
        # già le candidate: la funzione mantiene un controllo utile se usata da sola.
        if not set(strategy.addressed_vulnerabilities) <= known_cves:
            conflicts.append("Strategy references a vulnerability absent from the report")
        valid = not missing and not conflicts
        # Lo schema dell'esito verifica che flag, stato ed elenchi siano coerenti.
        # La spiegazione e il backend rendono visibile il carattere simulato del controllo.
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
