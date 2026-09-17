"""Controlli in sola lettura per la demo con i backend mock del prototipo.

Non pubblica né ripara artefatti. Ricontrolla i contratti dai file e verifica
la consegna dei tool nei messaggi SDK, senza avviare inferenza.
"""

import ast
import hashlib
import json
import re
from collections import Counter
from pathlib import Path

from thesis_agents.orchestration.artifacts import ARTIFACT_PRODUCERS, ARTIFACT_SCHEMAS
from thesis_agents.orchestration.explanations import build_explanation
from thesis_agents.schemas import DecisionContext, StaticTelemetry
from thesis_agents.tools.ranking_mock import MockRankingTool, build_graph
from thesis_agents.tools.semantic_mock import MockSemanticTool
from thesis_agents.tools.vulnerability_mock import MockVulnerabilityTool


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _tool_content(content):
    # CAMEL 0.2.90 può serializzare il risultato del tool come repr Python.
    if not isinstance(content, str):
        return content
    try:
        return json.loads(content)
    except ValueError:
        try:
            return ast.literal_eval(content)
        except (ValueError, SyntaxError):
            return None


def audit_run(run: Path, expected_input: StaticTelemetry, *, mode: str, model: str | None):
    """Valida una cartella del runner; restituisce anche errori e output parziali."""
    result = {"artifacts": {}, "checks": {}, "errors": [], "llm_requests": 0}
    values = {}
    domain = run / "artifacts"
    for name, schema in {"input": StaticTelemetry, **ARTIFACT_SCHEMAS}.items():
        try:
            values[name] = schema.model_validate_json((domain / f"{name}.json").read_text())
            result["artifacts"][name] = "valid"
        except (OSError, ValueError) as exc:
            result["artifacts"][name] = "missing_or_invalid"
            result["errors"].append(f"{name}: {exc}")

    def check(name, condition):
        result["checks"][name] = bool(condition)

    if "input" in values:
        check("input_matches", values["input"] == expected_input)
    if "final_decision" in values:
        decision = values["final_decision"]
        result.update(
            decision_status=decision.status, selected_strategy_id=decision.selected_strategy_id
        )

    if len(values) == len(ARTIFACT_SCHEMAS) + 1:
        try:
            case = values["input"]
            evidence = values["runtime_evidence"]
            report = values["vulnerability_report"]
            candidates = values["candidate_strategies"]
            graph = values["argumentation_graph"]
            ranking = values["ranking"]
            validations = values["semantic_validation"]
            provenance = values["provenance"]
            check(
                "runtime_matches_input",
                len(evidence.software) == 1
                and (
                    evidence.service_name,
                    evidence.software[0].package,
                    evidence.software[0].version,
                    evidence.endpoint_exposed,
                    evidence.deserialization_observed,
                )
                == (
                    case.service_name,
                    case.package_name,
                    case.package_version,
                    case.endpoint_exposed,
                    case.deserialization_observed,
                ),
            )
            lookup = MockVulnerabilityTool().lookup_vulnerabilities(evidence.software[0])
            check(
                "lookup_matches_backend",
                report.asset_id == case.service_name
                and report.lookup_status == lookup.status
                and report.vulnerabilities == lookup.vulnerabilities,
            )
            known = {v.cve_id for v in report.vulnerabilities}
            check(
                "candidates_grounded",
                bool(candidates.strategies) == bool(known)
                and all(set(s.addressed_vulnerabilities) <= known for s in candidates.strategies),
            )
            check("graph_matches_candidates", graph == build_graph(candidates, graph.id))
            check("ranking_matches_backend", ranking == MockRankingTool().rank_graph(graph))
            by_id = {s.id: s for s in candidates.strategies}
            context = DecisionContext(
                evidence=evidence,
                vulnerabilities=report,
                available_capabilities=case.available_capabilities,
                prohibited_actions=case.prohibited_actions,
            )
            expected_validations = []
            for item in ranking.ranking:
                validation = MockSemanticTool().validate_countermeasure(
                    by_id[item.strategy_id], context
                )
                expected_validations.append(validation)
                if validation.valid:
                    break
            check(
                "semantic_sequence_matches_backend", validations.validations == expected_validations
            )
            accepted = next((v for v in expected_validations if v.valid), None)
            expected_status = (
                "selected"
                if accepted
                else (
                    "insufficient_evidence"
                    if report.lookup_status == "unsupported"
                    else "no_valid_strategy"
                )
            )
            check(
                "decision_matches_tools",
                decision.status == expected_status
                and decision.selected_strategy_id == (accepted.strategy_id if accepted else None)
                and decision.ranking == ranking.ranking
                and decision.semantic_validation == accepted
                and decision.evidence_ids == [s.evidence_id for s in evidence.software],
            )
            result["selected_action"] = (
                by_id[decision.selected_strategy_id].action if accepted else None
            )
            result["candidate_actions"] = [s.action for s in candidates.strategies]
            result["validation_attempts"] = [
                v.model_dump(mode="json") for v in validations.validations
            ]
            result["fallback_observed"] = bool(accepted and len(validations.validations) > 1)

            prefix = "fixture:" if mode == "fixtures" else ""
            producers = {name: prefix + producer for name, producer in ARTIFACT_PRODUCERS.items()}
            producers.update(
                input="StaticTelemetry",
                ranking=prefix + "StrategicAgent",
                semantic_validation=prefix + "StrategicAgent",
            )
            expected_claims = build_explanation(
                case,
                evidence,
                report,
                candidates,
                ranking,
                validations,
                decision.selected_strategy_id,
                producers,
            )
            check(
                "explanation_derived",
                decision.explanation_method == "artifact-derived-v1"
                and decision.explanation_claims == expected_claims
                and decision.agent_commentary is not None
                and decision.agent_commentary.verification == "unverified",
            )
            sources_resolved = 0
            for claim in decision.explanation_claims:
                for source in claim.sources:
                    value = values[source.artifact].model_dump(mode="json")
                    for token in source.pointer.split("/")[1:]:
                        token = token.replace("~1", "/").replace("~0", "~")
                        value = value[int(token)] if isinstance(value, list) else value[token]
                    sources_resolved += 1
            result["sources_resolved"] = sources_resolved
            check("provenance_mode", provenance.mode == mode and provenance.model == model)
            expected_entities = set(values) - {"provenance"}
            # Non si segue un filename arbitrario del record: i nomi sono quelli canonici.
            check(
                "provenance_hashes",
                len(provenance.entities) == len(expected_entities)
                and {e.id for e in provenance.entities} == expected_entities
                and all(
                    e.filename == f"{e.id}.json" and sha256(domain / f"{e.id}.json") == e.sha256
                    for e in provenance.entities
                ),
            )
            generated_by = {name: a.agent for a in provenance.activities for name in a.generated}
            check(
                "provenance_producers",
                all(
                    generated_by.get(name) == producer
                    for name, producer in producers.items()
                    if name != "input"
                ),
            )
            check(
                "provenance_dependencies",
                all(set(a.used + a.generated) <= expected_entities for a in provenance.activities)
                and any(
                    a.id == "decision" and set(a.used) == set(producers)
                    for a in provenance.activities
                ),
            )
        except (ValueError, KeyError, IndexError, TypeError, OSError) as exc:
            result["errors"].append(f"Cross-artifact audit: {exc}")

    text = (run / "run.log").read_text(errors="replace") if (run / "run.log").exists() else ""
    result["failed_task_attempts"] = sorted(
        set(re.findall(r"Task (\w+) failed \(attempt (\d+/\d+)\)", text))
    )
    if mode == "camel":
        _audit_messages(run, values, result)
    result["passed"] = (
        not result["errors"] and bool(result["checks"]) and all(result["checks"].values())
    )
    return result


def _audit_messages(run, values, result):
    # Contare messaggi di contesto non equivale a contare chiamate: la cronologia
    # viene ripetuta nelle richieste. Le richieste/tool call sono contate a parte.
    contexts, decisions = [], []
    roles, calls = Counter(), Counter()
    files = sorted((run / "llm").rglob("*.json"))
    result["llm_requests"] = len(files)
    expected = {name: value.model_dump(mode="json") for name, value in values.items()}
    for path in files:
        try:
            log = json.loads(path.read_text())
            messages = log["request"]["messages"]
            system = str(messages[0].get("content", "")) if messages else ""
            role = next(
                (
                    r
                    for r in (*ARTIFACT_PRODUCERS.values(), "StrategicAgent")
                    if f"You are {r}." in system
                ),
                "management",
            )
            roles[role] += 1
            for choice in (log.get("response") or {}).get("choices", []):
                for call in choice.get("message", {}).get("tool_calls") or []:
                    calls[call["function"]["name"]] += 1
            if role != "StrategicAgent":
                continue
            for message in messages:
                if message.get("role") != "tool":
                    continue
                content = _tool_content(message.get("content"))
                if not isinstance(content, dict):
                    continue
                if "artifact_producers" in content:
                    contexts.append(
                        all(
                            name in expected
                            and content.get("artifacts", {}).get(name) == expected[name]
                            and content["artifact_producers"].get(name) == producer
                            for name, producer in ARTIFACT_PRODUCERS.items()
                        )
                    )
                if "explanation_method" in content:
                    decisions.append(content == expected.get("final_decision"))
        except (OSError, ValueError, KeyError, TypeError, AttributeError) as exc:
            result["errors"].append(f"SDK log {path.name}: {exc}")
    result["requests_by_role"] = dict(roles)
    result["tool_calls"] = dict(calls)
    result["strategic_context_messages_verified"] = sum(contexts)
    result["decision_tool_messages_verified"] = sum(decisions)
    result["checks"]["four_agent_inference"] = all(
        roles[r] > 0 for r in (*ARTIFACT_PRODUCERS.values(), "StrategicAgent")
    )
    result["checks"]["strategic_inputs_delivered"] = bool(contexts) and all(contexts)
    result["checks"]["decision_delivered"] = bool(decisions) and all(decisions)


def scenario_matches(scenario: str, audit: dict) -> bool:
    """Aspettative di dominio senza imporre al modello punteggi o ID delle fixture."""
    status = audit.get("decision_status")
    if scenario == "demo_01_nominal":
        return status == "selected"
    if scenario == "demo_02_no_maintenance":
        return status == "selected" and audit.get("selected_action") != "upgrade"
    if scenario == "demo_03_all_actions_prohibited":
        return (
            status == "no_valid_strategy"
            and bool(audit.get("validation_attempts"))
            and all(
                not v["valid"]
                and any(c.startswith("Action prohibited by scenario:") for c in v["conflicts"])
                for v in audit["validation_attempts"]
            )
        )
    return (
        scenario == "demo_04_unsupported_lookup"
        and status == "insufficient_evidence"
        and (audit.get("candidate_actions") == [] and audit.get("validation_attempts") == [])
    )
