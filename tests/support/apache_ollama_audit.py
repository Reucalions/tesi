"""Audit offline della prova Apache/Ollama; non modifica artefatti di dominio."""

import argparse
import json
import re
from pathlib import Path

from rdflib import RDF, Dataset, Namespace, URIRef

from thesis_agents.demo import write_json
from thesis_agents.demo_audit import _audit_messages, _tool_content, sha256
from thesis_agents.mcp.client import digest
from thesis_agents.mcp.ubuntu_contracts import PackageAssessment
from thesis_agents.orchestration.artifacts import ARTIFACT_PRODUCERS, ARTIFACT_SCHEMAS
from thesis_agents.orchestration.explanations import build_explanation
from thesis_agents.provenance import export_prov
from thesis_agents.schemas import VulnerabilityReport
from thesis_agents.schemas.telemetry_source import TelemetryInput, TelemetrySnapshot
from thesis_agents.schemas.verification import PackageVerificationContext
from thesis_agents.tools.package_verification import package_verification_context
from thesis_agents.tools.telemetry_http import evidence_from_snapshot
from thesis_agents.tools.ubuntu_mcp import map_ubuntu_assessment


def audit(run):
    root = Path(__file__).resolve().parents[2]
    manifest = json.loads((run / "manifest.json").read_text())
    execution = json.loads((run / "execution.json").read_text())
    result = {"llm_used": True, "artifacts": {}, "checks": {}, "errors": [], **execution}
    values = {}
    schemas = {
        "input": TelemetryInput,
        **ARTIFACT_SCHEMAS,
        "telemetry_snapshot": TelemetrySnapshot,
        "ubuntu_package_assessment": PackageAssessment,
        "package_verification_context": PackageVerificationContext,
    }
    domain = run / "artifacts"
    for name, schema in schemas.items():
        try:
            values[name] = schema.model_validate_json((domain / f"{name}.json").read_text())
            result["artifacts"][name] = "valid"
        except (OSError, ValueError) as exc:
            result["artifacts"][name] = "missing_or_invalid"
            result["errors"].append(f"{name}: {exc}")

    def check(name, condition):
        result["checks"][name] = bool(condition)

    check("cli_completed", execution.get("exit_code") == 0)
    check("source_code_unchanged", execution.get("source_code_unchanged") is True)
    check(
        "manifest_sources_match",
        all(
            sha256((run / "source-snapshot" if (run / "source-snapshot").exists() else root) / p)
            == h
            for p, h in manifest["source_hashes"].items()
        ),
    )
    _audit_messages(run, values, result)
    if len(values) == len(schemas):
        try:
            case, evidence, report, candidates, ranking, validations, decision, record = (
                values[name]
                for name in (
                    "input",
                    "runtime_evidence",
                    "vulnerability_report",
                    "candidate_strategies",
                    "ranking",
                    "semantic_validation",
                    "final_decision",
                    "provenance",
                )
            )
            check(
                "runtime_matches_snapshot",
                evidence == evidence_from_snapshot(values["telemetry_snapshot"]),
            )
            mapped = map_ubuntu_assessment(
                values["ubuntu_package_assessment"], values["telemetry_snapshot"]
            )
            expected = VulnerabilityReport(
                asset_id=evidence.service_name,
                lookup_status=mapped.status,
                vulnerabilities=mapped.vulnerabilities,
                package_assessment=mapped.package_assessment,
            )
            check("report_matches_backend", report == expected)
            check(
                "package_counts",
                report.package_assessment.counts
                == {"fixed": 34, "not_affected": 28, "potentially_affected": 46, "unknown": 12},
            )
            context = package_verification_context(evidence, report)
            check("verification_context_derived", context == values["package_verification_context"])
            check(
                "requests_preserved",
                candidates.verification_requests == context.verification_requests,
            )
            check("no_unconfirmed_strategies", candidates.strategies == [])
            check(
                "ranking_abstained",
                ranking.backend == "empty-strategy-gate-v1" and ranking.ranking == [],
            )
            check("no_semantic_validation", validations.validations == [])
            check(
                "decision_consistent",
                decision.status == "insufficient_evidence"
                and decision.selected_strategy_id is None,
            )
            producers = {
                **ARTIFACT_PRODUCERS,
                "input": "TelemetryInput",
                "ranking": "StrategicAgent",
                "semantic_validation": "StrategicAgent",
            }
            check(
                "explanation_derived",
                decision.explanation_claims
                == build_explanation(
                    case, evidence, report, candidates, ranking, validations, None, producers
                ),
            )
            for claim in decision.explanation_claims:
                for source in claim.sources:
                    value = values[source.artifact].model_dump(mode="json")
                    for token in source.pointer.split("/")[1:]:
                        token = token.replace("~1", "/").replace("~0", "~")
                        value = value[int(token)] if isinstance(value, list) else value[token]
            check("explanation_pointers_resolve", True)
            check(
                "provenance_hashes",
                all(
                    e.filename == f"{e.id}.json" and sha256(domain / f"{e.id}.json") == e.sha256
                    for e in record.entities
                ),
            )
            document = json.loads((domain / "provenance.jsonld").read_text())
            receipt = json.loads((domain / "provenance_receipt.json").read_text())
            check("prov_export_derived", document == export_prov(record))
            check(
                "receipt_bound",
                receipt["record_sha256"] == digest(record.model_dump(mode="json"))
                and receipt["jsonld_sha256"] == digest(document)
                and receipt["run_id"] == record.run_id,
            )
            check(
                "no_ledger_claim",
                receipt["storage_kind"] == "artifact-files"
                and receipt["ledger_status"] == "not_submitted",
            )
            dataset = Dataset()
            dataset.parse(data=json.dumps(document), format="json-ld")
            graph = dataset.graph(URIRef(document["@id"]))
            prov = Namespace("http://www.w3.org/ns/prov#")
            check(
                "rdf_entities_preserved",
                len(set(graph.subjects(RDF.type, prov.Entity))) == len(record.entities),
            )
            check(
                "rdf_activities_preserved",
                len(set(graph.subjects(RDF.type, prov.Activity))) == len(record.activities),
            )
            events = [
                json.loads(line) for line in (domain / "mcp_events.jsonl").read_text().splitlines()
            ]
            calls = [e for e in events if e["event"] == "tool_call"]
            check("mcp_calls_validated", all(e["status"] == "validated" for e in calls))
            check("provenance_readback", any(e["tool"] == "read_provenance" for e in calls))
            result.update(
                decision_status=decision.status,
                package_counts=report.package_assessment.counts,
                verification_requests=len(candidates.verification_requests),
                rdf_triples=len(graph),
                mcp_calls=[{"role": e["backend_role"], "tool": e["tool"]} for e in calls],
            )
        except (OSError, ValueError, KeyError, TypeError, IndexError) as exc:
            result["errors"].append(f"Cross-artifact audit: {exc}")
    usages, finish_reasons, countermeasure_contexts, textual_tool_attempts = [], [], [], []
    textual_artifact_attempts = []
    for path in sorted((run / "llm").rglob("*.json")):
        log = json.loads(path.read_text())
        response = log.get("response") or {}
        usages.append(response.get("usage") or {})
        finish_reasons.extend(c.get("finish_reason") for c in response.get("choices", []))
        for choice in response.get("choices", []):
            message = choice.get("message", {})
            content = _tool_content(message.get("content"))
            if (
                not message.get("tool_calls")
                and isinstance(message.get("content"), str)
                and re.search(r'"payload"\s*:\s*\{\s*"strategies"', message["content"])
                and not re.search(r'"name"\s*:', message["content"])
            ):
                textual_artifact_attempts.append(str(path.relative_to(run)))
            if (
                not message.get("tool_calls")
                and isinstance(content, dict)
                and "name" in content
                and "arguments" in content
            ):
                textual_tool_attempts.append(
                    {"file": str(path.relative_to(run)), "name": content["name"]}
                )
            elif not message.get("tool_calls") and isinstance(message.get("content"), str):
                match = re.search(
                    r'"name"\s*:\s*"(publish_[a-z_]+|record_provenance)"', message["content"]
                )
                if match:
                    textual_tool_attempts.append(
                        {"file": str(path.relative_to(run)), "name": match[1]}
                    )
        messages = log.get("request", {}).get("messages", [])
        if messages and "You are CountermeasureAgent." in str(messages[0].get("content", "")):
            for message in messages:
                if message.get("role") != "tool":
                    continue
                context = _tool_content(message.get("content"))
                if isinstance(context, dict) and "artifact_producers" in context:
                    countermeasure_contexts.append(
                        all(
                            name in values
                            and context.get("artifacts", {}).get(name)
                            == values[name].model_dump(mode="json")
                            and context["artifact_producers"].get(name) == ARTIFACT_PRODUCERS[name]
                            for name in ("runtime_evidence", "vulnerability_report")
                        )
                    )
    result["endpoint_usage"] = {
        key: sum(u.get(key, 0) for u in usages)
        for key in ("prompt_tokens", "completion_tokens", "total_tokens")
    }
    result["truncated_responses"] = finish_reasons.count("length")
    result["textual_tool_attempts"] = textual_tool_attempts
    result["textual_artifact_attempts"] = textual_artifact_attempts
    result["llm_responses"] = sum(
        bool(json.loads(p.read_text()).get("response")) for p in (run / "llm").rglob("*.json")
    )
    result["max_prompt_tokens"] = max((u.get("prompt_tokens", 0) for u in usages), default=0)
    check(
        "countermeasure_inputs_delivered",
        bool(countermeasure_contexts) and all(countermeasure_contexts),
    )
    text = (run / "run.log").read_text(errors="replace")
    result["failed_task_attempts"] = sorted(
        set(re.findall(r"Task (\w+) failed \(attempt (\d+/\d+)\)", text))
    )
    result["passed"] = not result["errors"] and all(result["checks"].values())
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("run", type=Path)
    args = parser.parse_args()
    result = audit(args.run)
    write_json(args.run / "audit.json", result)
    print(json.dumps({k: v for k, v in result.items() if k != "errors"}, indent=2))
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
