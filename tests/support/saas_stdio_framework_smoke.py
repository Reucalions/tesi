"""Framework -> bridge stdio -> SaaS HTTP reali; Fabric/autenticazione simulati."""

import argparse
import json
import os
import subprocess
import time
from pathlib import Path

import httpx

from thesis_agents.mcp.client import MCPToolError
from thesis_agents.mcp.shared_client import SharedMCPProfile, SharedServicesClient
from thesis_agents.mcp.shared_contracts import (
    RankRemediationsRequest,
    ValidateCountermeasureRequest,
)


def smoke(node: Path, backend: Path, bridge: Path, output: Path):
    output.mkdir(exist_ok=False)
    environment = os.environ | {
        "SAAS_TEST_BACKEND": str(backend),
        "SAAS_TEST_STATE": str(output),
        "ARGUMENTATION_CHAINCODE": "argumentation",
        "SEMANTIC_CHAINCODE": "user-registry",
        "SEMANTIC_ONTOLOGY_KEY": "",
    }
    fixture = Path(__file__).with_name("saas_fixture.cjs")
    with (output / "backend.log").open("x") as log:
        process = subprocess.Popen(
            [str(node), str(fixture)], cwd=backend, env=environment, stdout=log, stderr=log
        )
        try:
            for _ in range(200):
                if (output / "ready.json").exists():
                    break
                if process.poll() is not None:
                    raise RuntimeError("Fixture startup failed; inspect backend.log")
                time.sleep(0.05)
            else:
                raise TimeoutError("Fixture did not start")
            url = json.loads((output / "ready.json").read_text())["url"]
            os.environ["STDIO_SMOKE_REST_URL"] = url
            os.environ["STDIO_SMOKE_USER"] = "fixture"
            profile = SharedMCPProfile.model_validate(
                {
                    "connection": {
                        "transport": "mcp-stdio",
                        "command": str(node),
                        "args": [str(bridge / "build/index.js")],
                        "cwd": str(bridge),
                        "env_from": {
                            "FABLO_REST_URL": "STDIO_SMOKE_REST_URL",
                            "FABLO_USER": "STDIO_SMOKE_USER",
                        },
                        "expected_kind": "real",
                        "timeout_seconds": 15,
                    },
                }
            )
            (output / "profile.json").write_text(profile.model_dump_json(indent=2) + "\n")
            events = []

            def connect(label):
                return SharedServicesClient(
                    profile, audit=events.append, stderr_path=output / f"{label}.stderr.log"
                )

            request = RankRemediationsRequest(
                cve_id="CVE-2025-0160",
                candidates=[
                    {"id": "S_PATCH", "name": "Patch"},
                    {"id": "S_ISOLATE", "name": "Isolate"},
                ],
                knowledge_snapshot_id="urn:cti:snapshot:cve2owl:v1.0.0",
                asset_context={"productName": "Apache HTTP Server", "version": "2.4.49"},
            )
            (output / "rank-request.json").write_text(request.model_dump_json(indent=2) + "\n")
            with httpx.Client(base_url=url, timeout=15, trust_env=False) as http:
                rest = http.post("/api/v1/remediations/rank", json=request.rest_payload())
                assert rest.status_code == 200, rest.text
                with connect("main") as client:
                    ranking = client.rank_remediations(request)
                    assert (
                        ranking.model_dump(by_alias=True, exclude_none=True)["rankedStrategies"]
                        == rest.json()["rankedStrategies"]
                    )
                    assert (
                        ranking.slsa_assurance.input_digest
                        == rest.json()["slsaAssurance"]["inputDigest"]
                    )
                    assert ranking.slsa_assurance.verified is False
                    decision = client.get_decision(ranking.decision_id)
                    provenance = client.get_provenance(ranking.decision_id)
                    semantic = []
                    for cm, status in [
                        ("cm-ok", "accepted"),
                        ("cm-needs", "requires_prerequisites"),
                        ("cm-conflict", "rejected"),
                    ]:
                        response = client.validate_countermeasure(
                            ValidateCountermeasureRequest(
                                asset_iri="asset", countermeasure_iri=cm, ontology_id="fixture-tbox"
                            )
                        )
                        assert response.status == status
                        semantic.append(response.model_dump(mode="json", by_alias=True))
                    server_info = client.client.server_info
            errors = []
            for cm, expected in [
                ("cm-timeout", "BACKEND_UNAVAILABLE"),
                ("cm-malformed", "INVALID_BACKEND_RESPONSE"),
            ]:
                with connect(cm) as client:
                    try:
                        client.validate_countermeasure(
                            ValidateCountermeasureRequest(
                                asset_iri="asset", countermeasure_iri=cm, ontology_id="fixture-tbox"
                            )
                        )
                    except MCPToolError as exc:
                        assert exc.code == expected
                        assert client.client._session is None
                        errors.append(exc.code)
                    else:
                        raise AssertionError("Technical failure accepted as a semantic result")
            with connect("bad-ranking") as client:
                try:
                    client.rank_remediations(
                        RankRemediationsRequest(
                            cve_id="CVE-2025-0160",
                            candidates=[{"id": "S_BROKEN", "name": "Broken"}],
                        )
                    )
                except MCPToolError as exc:
                    assert exc.code == "INVALID_BACKEND_RESPONSE"
                    errors.append(exc.code)
                else:
                    raise AssertionError("Malformed ranking accepted")
            (output / "mcp_events.jsonl").write_text("".join(json.dumps(e) + "\n" for e in events))
            report = {
                "success": True,
                "client": "thesis_agents.mcp.shared_client.SharedServicesClient",
                "server": server_info,
                "fabric": "simulated",
                "authentication": "fixture",
                "ledger_commit_verified": False,
                "rest_mcp_rank_parity": True,
                "ranking": ranking.model_dump(mode="json", by_alias=True, exclude_none=True),
                "decision": decision.model_dump(mode="json", by_alias=True, exclude_none=True),
                "provenance": provenance.model_dump(mode="json", by_alias=True, exclude_none=True),
                "semantic": semantic,
                "errors": errors,
            }
            (output / "results.json").write_text(json.dumps(report, indent=2) + "\n")
            print(
                json.dumps(
                    {
                        "success": True,
                        "output": str(output),
                        "calls": sum(e["event"] == "tool_call" for e in events),
                    }
                )
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
    smoke(args.node.resolve(), args.backend.resolve(), args.bridge.resolve(), args.output.resolve())
