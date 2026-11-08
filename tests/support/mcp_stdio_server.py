"""Processo stdio per test: nessuna porta, guasti confinati alla fixture."""

import argparse
import asyncio
import json
import os
import sys
import time
from pathlib import Path


def shared_server(fault):
    from mcp.server.lowlevel import Server
    from mcp.server.stdio import stdio_server
    from mcp.types import CallToolResult, TextContent, Tool

    from thesis_agents.mcp.client import digest
    from thesis_agents.mcp.shared_contracts import RankRemediationsRequest, shared_contracts

    server = Server("unrelated" if fault == "wrong-server" else "mcp-semantic-cti-saas")
    decisions = {}
    finalizations = {}

    @server.list_tools()
    async def tools():
        schemas = shared_contracts()
        from thesis_agents.mcp.finalization_contracts import finalization_contracts

        schemas.update(finalization_contracts())
        if fault == "missing":
            schemas.pop("get_provenance")
        if fault == "bad-schema":
            schemas["get_provenance"][0]["required"] = []
        return [Tool(name=name, inputSchema=schemas[name][0]) for name in schemas]

    @server.call_tool()
    async def call(name, arguments):
        if fault == "disconnect":
            os._exit(2)
        if fault == "timeout":
            await asyncio.sleep(20)
        if fault == "tool-error":
            return CallToolResult(
                isError=True,
                content=[
                    TextContent(
                        type="text",
                        text=json.dumps(
                            {
                                "ok": False,
                                "action": name,
                                "errorCode": "BACKEND_UNAVAILABLE",
                                "message": "ARBITRARY_REMOTE_SECRET",
                            }
                        ),
                    )
                ],
            )
        if name == "rank_remediations":
            request = RankRemediationsRequest.model_validate(arguments)
            assurance = {
                "builderId": "fixture",
                "chaincodeDigest": "",
                "verified": False,
                "ontologyDigest": "sha256:" + "a" * 64,
                "inputDigest": "sha256:" + digest(request.rest_payload()),
            }
            payload = {
                "decisionId": "DEC_TEST"
                if fault == "duplicate-decision"
                else f"DEC_{request.cve_id}",
                "cveId": request.cve_id,
                "tenantId": "fixture",
                "status": "CURRENT",
                "revision": 1,
                "rankedStrategies": [
                    {"id": c.id, "name": c.name, "rank": i, "score": 10.0 / i}
                    for i, c in enumerate(request.candidates, 1)
                ],
                "slsaAssurance": assurance,
                "knowledgeSnapshotId": request.knowledge_snapshot_id,
                "knowledgeSnapshotDigest": "sha256:" + "b" * 64,
                "timestamp": "fixture-time",
                "annotatedGraphKey": "GRAPH_" + request.cve_id + "_annotated_graph",
            }
            if fault == "wrong-cve":
                payload["cveId"] = "CVE-2025-99999"
            if fault == "wrong-candidate":
                payload["rankedStrategies"][0]["id"] = "unrelated"
            if fault == "bad-score":
                payload["rankedStrategies"][0]["score"] = "0.9"
            if fault in ("tied-scores", "negative-scores", "zero-score"):
                for row in payload["rankedStrategies"]:
                    row["score"] = (
                        7.5
                        if fault == "tied-scores"
                        else -float(row["rank"])
                        if fault == "negative-scores"
                        else 0.0
                    )
            if fault == "wrong-digest":
                assurance["inputDigest"] = "sha256:" + "0" * 64
            if fault == "wrong-snapshot":
                payload["knowledgeSnapshotId"] = "unrelated"
            decisions[payload["decisionId"]] = json.loads(json.dumps(payload))
        elif name == "validate_countermeasure":
            native = {
                "resourceIRI": arguments["asset_iri"],
                "score": 98,
                "topPenalty": 0,
                "abductionPenalty": 0,
                "contractionPenalty": 2,
                "hypothesis": "",
                "giveUp": "Fixture conflict",
                "keep": "",
            }
            payload = {
                "valid": False,
                "status": "rejected",
                "affinityScore": 0.98,
                "conflictPenalty": 2,
                "missingFeatures": [],
                "bonusFeatures": [],
                "bonusEvaluated": False,
                "explanation": "Fixture conflict",
                "timestamp": "fixture",
                "reasoning": {
                    "contract": "explain-affinity-v1",
                    "ontologyKey": arguments.get("ontology_id", "fixture"),
                    "resourceIRI": arguments["asset_iri"],
                    "requestIRI": arguments["countermeasure_iri"],
                    "native": native,
                },
            }
            if fault == "wrong-iri":
                payload["reasoning"]["requestIRI"] = "unrelated"
            if fault == "wrong-ontology":
                payload["reasoning"]["ontologyKey"] = "unrelated"
            if fault == "false-acceptance":
                payload.update(valid=True, status="accepted")
            if "operational_context" in arguments:
                from thesis_agents.mcp.operational_contracts import (
                    ACTION_REQUIREMENTS,
                    effective_status,
                )

                context = arguments["operational_context"]
                required = sorted(
                    set(ACTION_REQUIREMENTS[context["action"]])
                    | set(context["prerequisites"])
                    | {
                        capability
                        for mapping in context["constraint_mappings"]
                        for capability in mapping["required_capabilities"]
                    }
                )
                missing = sorted(set(required) - set(context["available_capabilities"]))
                prohibited = context["action"] in context["prohibited_actions"]
                mapped = {mapping["constraint"] for mapping in context["constraint_mappings"]}
                unassessed = sorted(set(context["constraints"]) - mapped)
                op_status = (
                    "rejected"
                    if prohibited
                    else "requires_prerequisites"
                    if missing
                    else "requires_review"
                    if unassessed
                    else "accepted"
                )
                # Explicit service simulation: accepted native result unless a fault is requested.
                semantic_rejected = (
                    fault == "semantic-rejected"
                    or (
                        fault == "semantic-first-rejected"
                        and context["ontology_individual"].endswith("_0")
                    )
                    or (
                        fault == "semantic-one-cve-rejected"
                        and context["cve_id"] == "CVE-2021-44228"
                    )
                )
                if fault != "false-acceptance" and not semantic_rejected:
                    payload.update(
                        valid=True,
                        status="accepted",
                        conflictPenalty=0,
                        affinityScore=1.0,
                        reasoning={
                            **payload["reasoning"],
                            "native": {
                                **native,
                                "score": 100,
                                "contractionPenalty": 0,
                                "hypothesis": "Thing",
                                "giveUp": "",
                            },
                        },
                    )
                    payload["explanation"] = "Simulated semantic compatibility"
                    if fault == "semantic-needs":
                        payload.update(
                            valid=False,
                            status="requires_prerequisites",
                            affinityScore=0.99,
                            missingFeatures=["Required semantic feature"],
                        )
                        payload["reasoning"]["native"].update(
                            score=99, abductionPenalty=1, hypothesis="Required semantic feature"
                        )
                payload["operational"] = {
                    "contract": "operational-assessment-v1",
                    "context_digest": "sha256:" + digest(context),
                    "policy_id": context["policy_id"],
                    "policy_digest": context["policy_digest"],
                    "required_capabilities": required,
                    "missing_capabilities": missing,
                    "prohibited_action": prohibited,
                    "unassessed_constraints": unassessed,
                    "evaluator": "saas_operational_policy",
                    "status": op_status,
                }
                payload["effectiveStatus"] = effective_status(payload["status"], op_status)
                if fault == "operational-omitted":
                    payload.pop("operational")
                    payload.pop("effectiveStatus")
                elif fault == "operational-false-acceptance":
                    payload["operational"].update(
                        status="accepted", missing_capabilities=[], prohibited_action=False
                    )
                    payload["effectiveStatus"] = "accepted"
                elif fault == "operational-digest":
                    payload["operational"]["context_digest"] = "sha256:" + "0" * 64
        elif name == "finalize_recommendation":
            from finalization_fixture import response_for

            from thesis_agents.mcp.finalization_contracts import FinalizationDocument

            doc = FinalizationDocument.model_validate_json(arguments["document_json"])
            payload = response_for(
                arguments["document_json"], decisions[doc.ranking_decision_id]["slsaAssurance"]
            )
            if fault == "finalization-commit":
                payload["commit"]["successful"] = False
            if fault == "finalization-digest":
                payload["record"]["document_sha256"] = "sha256:" + "0" * 64
            finalizations[doc.finalization_id] = json.loads(json.dumps(payload))
        elif name == "get_finalization":
            payload = json.loads(json.dumps(finalizations[arguments["finalization_id"]]))
            if fault == "finalization-readback":
                payload["commit"]["block_number"] = "43"
        else:
            original = decisions[arguments["decision_id"]]
            assurance = original["slsaAssurance"]
            payload = {
                k: original[k]
                for k in (
                    "decisionId",
                    "knowledgeSnapshotId",
                    "knowledgeSnapshotDigest",
                )
            }
            payload["slsaAssurance"] = dict(assurance)
            if name == "get_decision":
                payload.update(
                    {
                        k: original[k]
                        for k in (
                            "cveId",
                            "tenantId",
                            "status",
                            "revision",
                            "rankedStrategies",
                        )
                    }
                )
                payload.update(
                    inputDigest=assurance["inputDigest"],
                    ontologyDigest=assurance["ontologyDigest"],
                    createdAt="fixture",
                    updatedAt="fixture",
                )
                if fault == "read-cve":
                    payload["cveId"] = "CVE-2025-99999"
                if fault == "read-status":
                    payload["status"] = "STALE"
                if fault == "read-ontology":
                    payload["ontologyDigest"] = "sha256:" + "c" * 64
                if fault == "read-no-assurance":
                    payload.pop("slsaAssurance")
            else:
                payload.update(context={}, entities=[], activities=[], agents=[], relations=[])
                if fault == "read-assurance":
                    payload["slsaAssurance"]["verified"] = True
                    payload["slsaAssurance"]["chaincodeDigest"] = "sha256:" + "c" * 64
            if fault == "read-snapshot":
                payload["knowledgeSnapshotDigest"] = "sha256:" + "c" * 64
        envelope = {"ok": True, "action": name, "payload": payload}
        if fault == "wrong-action":
            envelope["action"] = "unrelated"
        return [TextContent(type="text", text=json.dumps(envelope))]

    async def run():
        async with stdio_server() as (reader, writer):
            await server.run(reader, writer, server.create_initialization_options())

    asyncio.run(run())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--kind", choices=("lookup", "lookup-real-fixture", "strategic", "shared"), default="lookup"
    )
    parser.add_argument("--fault", default="none")
    parser.add_argument("--pid-file", type=Path, required=True)
    parser.add_argument("--state-file", type=Path)
    parser.add_argument("--literal", default="")
    args = parser.parse_args()
    args.pid_file.write_text(str(os.getpid()))
    if args.state_file:
        args.state_file.write_text(
            json.dumps(
                {
                    "literal": args.literal,
                    "explicit": os.getenv("CHILD_SENTINEL"),
                    "unmapped": os.getenv("UNMAPPED_SENTINEL"),
                }
            )
        )
    print("Fixture stderr, stdout riservato a MCP", file=sys.stderr, flush=True)
    if args.fault == "startup-timeout":
        time.sleep(20)
    if args.kind == "shared":
        shared_server(args.fault)
        return
    if args.kind == "lookup-real-fixture":
        # Test-only service metadata; data/infrastructure remain synthetic, never live CTI.
        from mcp.server.fastmcp import FastMCP

        from thesis_agents.mcp.contracts import LOOKUP_CONTRACT, LookupResponse
        from thesis_agents.schemas import SoftwareObservation
        from thesis_agents.tools.vulnerability_mock import MockVulnerabilityTool

        server = FastMCP("synthetic-real-mode-cti-fixture", log_level="WARNING")

        @server.tool()
        def lookup_vulnerabilities(software: SoftwareObservation) -> LookupResponse:
            result = MockVulnerabilityTool().lookup_vulnerabilities(software)
            if args.fault == "unsupported":
                result = result.model_copy(update={"status": "unsupported", "vulnerabilities": []})
            return LookupResponse(
                contract=LOOKUP_CONTRACT,
                backend_kind="real",
                backend="test-only-synthetic-cti",
                result=result,
            )

        server.run(transport="stdio")
        return
    from thesis_agents.mcp.mock_server import create_server
    from thesis_agents.mcp.strategic_mock_server import create_server as strategic_server

    server = (
        strategic_server(data_dir=args.pid_file.parent / "store")
        if args.kind == "strategic"
        else create_server()
    )
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
