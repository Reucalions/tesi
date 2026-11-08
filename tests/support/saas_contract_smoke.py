"""Collaudo REST/MCP effettivo, con Fabric e autenticazione esplicitamente simulati."""

import argparse
import asyncio
import json
import os
import subprocess
from pathlib import Path

import httpx
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client


async def smoke(node: Path, backend: Path, bridge: Path, output: Path):
    output.mkdir(exist_ok=False)
    environment = os.environ | {
        "SAAS_TEST_BACKEND": str(backend),
        "SAAS_TEST_STATE": str(output),
        "ARGUMENTATION_CHAINCODE": "argumentation",
        "SEMANTIC_CHAINCODE": "user-registry",
        "SEMANTIC_ONTOLOGY_KEY": "",
    }
    fixture = Path(__file__).with_name("saas_fixture.cjs")
    with (output / "backend.log").open("w") as log:
        process = subprocess.Popen(
            [str(node), str(fixture)], cwd=backend, env=environment, stdout=log, stderr=log
        )
        try:
            for _ in range(200):
                if (output / "ready.json").exists():
                    break
                if process.poll() is not None:
                    raise RuntimeError("Fixture startup failed; inspect backend.log")
                await asyncio.sleep(0.05)
            else:
                raise TimeoutError("Fixture did not start")
            url = json.loads((output / "ready.json").read_text())["url"]
            params = StdioServerParameters(
                command=str(node),
                args=[str(bridge / "build/index.js")],
                cwd=str(bridge),
                env=environment | {"FABLO_REST_URL": url, "FABLO_USER": "fixture"},
            )
            with (output / "mcp.log").open("w") as mcp_log:
                async with stdio_client(params, errlog=mcp_log) as (reader, writer):
                    async with ClientSession(reader, writer) as session:
                        await session.initialize()
                        tools = (await session.list_tools()).tools
                        assert len(tools) == 19
                        rank_schema = next(
                            t.inputSchema for t in tools if t.name == "rank_remediations"
                        )
                        assert {"knowledge_snapshot_id", "ontology_version"} <= rank_schema[
                            "properties"
                        ].keys()

                        async def call(name, payload, *, error=False):
                            result = await session.call_tool(name, payload)
                            envelope = json.loads(result.content[0].text)
                            assert bool(result.isError) == error
                            assert envelope["ok"] != error and envelope["action"] == name
                            return envelope

                        async with httpx.AsyncClient(
                            base_url=url, timeout=10, trust_env=False
                        ) as http:
                            candidates = [
                                {"id": "S_PATCH", "name": "Patch"},
                                {"id": "S_ISOLATE", "name": "Isolate"},
                            ]
                            snapshot = "urn:cti:snapshot:cve2owl:v1.0.0"
                            rest = await http.post(
                                "/api/v1/remediations/rank",
                                json={
                                    "cveId": "CVE-2025-0160",
                                    "candidates": candidates,
                                    "knowledgeSnapshotId": snapshot,
                                },
                            )
                            assert rest.status_code == 200, rest.text
                            mcp = (
                                await call(
                                    "rank_remediations",
                                    {
                                        "cve_id": "CVE-2025-0160",
                                        "candidates": candidates,
                                        "knowledge_snapshot_id": snapshot,
                                    },
                                )
                            )["payload"]
                            assert mcp["rankedStrategies"] == rest.json()["rankedStrategies"]
                            assert mcp["knowledgeSnapshotId"] == snapshot
                            assert (
                                mcp["slsaAssurance"]["inputDigest"]
                                == rest.json()["slsaAssurance"]["inputDigest"]
                            )
                            assert mcp["slsaAssurance"]["verified"] is False
                            decision = (
                                await call("get_decision", {"decision_id": mcp["decisionId"]})
                            )["payload"]
                            provenance = (
                                await call("get_provenance", {"decision_id": mcp["decisionId"]})
                            )["payload"]
                            assert decision["rankedStrategies"] == mcp["rankedStrategies"]
                            assert provenance["decisionId"] == mcp["decisionId"]
                            assert provenance["slsaAssurance"] == mcp["slsaAssurance"]
                            graph = (
                                await call(
                                    "get_graph",
                                    {
                                        "graph_id": mcp["annotatedGraphKey"].removesuffix(
                                            "_annotated_graph"
                                        ),
                                    },
                                )
                            )["payload"]
                            assert any(
                                node["id"] == "S_PATCH"
                                for node in json.loads(graph["response"]["success"])["nodes"]
                            )
                            semantic = []
                            for cm, expected in [
                                ("cm-ok", "accepted"),
                                ("cm-needs", "requires_prerequisites"),
                                ("cm-conflict", "rejected"),
                            ]:
                                rest = await http.post(
                                    "/api/v1/remediations/validate",
                                    json={
                                        "assetIri": "asset",
                                        "countermeasureIri": cm,
                                        "ontologyId": "fixture-tbox",
                                    },
                                )
                                assert rest.status_code == 200, rest.text
                                response = (
                                    await call(
                                        "validate_countermeasure",
                                        {
                                            "asset_iri": "asset",
                                            "countermeasure_iri": cm,
                                            "ontology_id": "fixture-tbox",
                                        },
                                    )
                                )["payload"]
                                assert response["status"] == expected
                                for field in [
                                    "valid",
                                    "status",
                                    "affinityScore",
                                    "conflictPenalty",
                                    "missingFeatures",
                                    "reasoning",
                                ]:
                                    assert response[field] == rest.json()[field]
                                semantic.append(response)
                            errors = []
                            for cm, status, code in [
                                ("cm-timeout", 503, "BACKEND_UNAVAILABLE"),
                                ("cm-malformed", 502, "INVALID_BACKEND_RESPONSE"),
                            ]:
                                rest = await http.post(
                                    "/api/v1/remediations/validate",
                                    json={
                                        "assetIri": "asset",
                                        "countermeasureIri": cm,
                                        "ontologyId": "fixture-tbox",
                                    },
                                )
                                assert rest.status_code == status and rest.json()["error"] == code
                                response = await call(
                                    "validate_countermeasure",
                                    {
                                        "asset_iri": "asset",
                                        "countermeasure_iri": cm,
                                        "ontology_id": "fixture-tbox",
                                    },
                                    error=True,
                                )
                                assert response["errorCode"] == code and "payload" not in response
                                errors.append({"http_status": status, "mcp": response})
                            invalid_rank = await call(
                                "rank_remediations",
                                {
                                    "cve_id": "CVE-2025-0160",
                                    "candidates": [{"id": "S_BROKEN", "name": "Broken"}],
                                },
                                error=True,
                            )
                            assert invalid_rank["errorCode"] == "INVALID_BACKEND_RESPONSE"
                            report = {
                                "success": True,
                                "fabric": "simulated",
                                "authentication": "fixture",
                                "transports": ["HTTP REST", "MCP stdio"],
                                "tools": [t.name for t in tools],
                                "ranking": mcp,
                                "semantic": semantic,
                                "errors": errors,
                                "malformed_ranking": invalid_rank,
                                "ledger_commit_verified": False,
                            }
                            (output / "results.json").write_text(
                                json.dumps(report, indent=2) + "\n"
                            )
        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for option in ("node", "backend", "bridge", "output"):
        parser.add_argument(f"--{option}", type=Path, required=True)
    args = parser.parse_args()
    asyncio.run(
        smoke(*(getattr(args, name).resolve() for name in ("node", "backend", "bridge", "output")))
    )
