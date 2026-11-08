"""Framework -> bridge stdio -> SaaS HTTP effettivi; Fabric/Tiny-ME simulati."""

import argparse
import json
import os
import subprocess
import time
from pathlib import Path

import httpx

from thesis_agents.canonical.preparation import bytes_digest
from thesis_agents.canonical.session import load_prepared_checkpoint
from thesis_agents.mcp.client import MCPToolError
from thesis_agents.mcp.operational_contracts import ACTION_REQUIREMENTS
from thesis_agents.mcp.shared_client import SharedMCPProfile, SharedServicesClient
from thesis_agents.strategic.contracts import NativeRankingSettings
from thesis_agents.strategic.session import NativeStrategicSession
from thesis_agents.strategic.validation_contracts import ValidationProfile
from thesis_agents.strategic.validation_session import NativeValidationSession


def finish(session):
    session.get_context()
    while operation := session.next_operation():
        arguments = dict(operation)
        getattr(session, arguments.pop("tool"))(**arguments)
    return session.assert_complete()


def smoke(node, backend, bridge, prepared, output):
    output.mkdir(exist_ok=False)
    preparation, inputs = load_prepared_checkpoint(prepared)
    environment = os.environ | {
        "SAAS_TEST_BACKEND": str(backend),
        "SAAS_TEST_STATE": str(output),
        "ARGUMENTATION_CHAINCODE": "argumentation",
        "SEMANTIC_CHAINCODE": "user-registry",
        "SEMANTIC_ONTOLOGY_KEY": "",
        "SAAS_TEST_SNAPSHOT_ID": preparation.knowledge_snapshot_id,
    }
    with (output / "backend.log").open("x") as log:
        process = subprocess.Popen(
            [str(node), str(Path(__file__).with_name("saas_fixture.cjs"))],
            cwd=backend,
            env=environment,
            stdout=log,
            stderr=log,
        )
        try:
            for _ in range(200):
                if (output / "ready.json").exists():
                    break
                if process.poll() is not None:
                    raise RuntimeError("SaaS fixture startup failed")
                time.sleep(0.05)
            else:
                raise TimeoutError("SaaS fixture did not start")
            url = json.loads((output / "ready.json").read_bytes())["url"]
            os.environ["OP_SMOKE_URL"], os.environ["OP_SMOKE_USER"] = url, "fixture"
            profile = SharedMCPProfile.model_validate(
                {
                    "connection": {
                        "command": str(node),
                        "args": [str(bridge / "build/index.js")],
                        "cwd": str(bridge),
                        "expected_kind": "real",
                        "env_from": {
                            "FABLO_REST_URL": "OP_SMOKE_URL",
                            "FABLO_USER": "OP_SMOKE_USER",
                        },
                        "timeout_seconds": 15,
                    }
                }
            )
            events = []
            with SharedServicesClient(
                profile, audit=events.append, stderr_path=output / "mcp.stderr.log"
            ) as client:
                # This is a transport fixture, not independent deployment attestation.
                probe = client.rank_remediations(preparation.graphs[0].ranking_request)
                (output / "probe.json").write_text(probe.model_dump_json(indent=2, by_alias=True))
                settings = NativeRankingSettings(
                    tenant_id=probe.tenant_id,
                    knowledge_snapshot_id=probe.knowledge_snapshot_id,
                    knowledge_snapshot_digest=probe.knowledge_snapshot_digest,
                    ontology_digest=probe.slsa_assurance.ontology_digest,
                )
                native = NativeStrategicSession(prepared, output / "ranking", settings, client)
                ranking = finish(native)
                (output / "ranking-result.json").write_text(
                    ranking.model_dump_json(indent=2, by_alias=True)
                )
                candidates = inputs["candidate_strategies"]["strategies"]
                mappings = [
                    {
                        "strategy_id": c["id"],
                        "constraint": text,
                        "required_capabilities": ["operator_approval_" + c["id"]],
                    }
                    for c in candidates
                    for text in c["constraints"]
                ]
                capabilities = {cap for caps in ACTION_REQUIREMENTS.values() for cap in caps}
                capabilities |= {cap for c in candidates for cap in c["prerequisites"]}
                capabilities |= {cap for m in mappings for cap in m["required_capabilities"]}
                base = dict(
                    run_id=ranking.run_id,
                    asset_id=ranking.asset_id,
                    ranking_sha256=bytes_digest(
                        (native.output_dir / "native_strategic_ranking.json").read_bytes()
                    ),
                    ontology_key="fixture-tbox",
                    asset_iri="urn:fixture:asset",
                    bindings=[
                        {
                            **b.model_dump(),
                            "countermeasure_iri": "urn:fixture:" + b.ontology_individual,
                        }
                        for result in ranking.results
                        for b in result.bindings
                    ],
                    available_capabilities=sorted(capabilities),
                    prohibited_actions=[],
                    constraint_mappings=mappings,
                    policy_source="Synthetic explicit operator policy",
                )
                cases = []
                for name, update, expected in [
                    ("accepted", {}, "accepted"),
                    ("missing", {"available_capabilities": []}, "requires_prerequisites"),
                    ("prohibited", {"prohibited_actions": list(ACTION_REQUIREMENTS)}, "rejected"),
                    ("unmapped", {"constraint_mappings": []}, "requires_review"),
                ]:
                    session = NativeValidationSession(
                        native.output_dir,
                        output / name,
                        ValidationProfile.model_validate(base | update),
                        client,
                    )
                    result = finish(session)
                    assert {a.response.effective_status for a in result.attempts} == {expected}
                    assert all(a.response.status == "accepted" for a in result.attempts)
                    cases.append(
                        {
                            "scenario": name,
                            "effective_status": expected,
                            "attempts": len(result.attempts),
                        }
                    )
                first = next(iter(session._requests.values())).model_copy(deep=True)
                semantic = []
                for suffix, expected in [
                    ("cm-needs", "requires_prerequisites"),
                    ("cm-conflict", "rejected"),
                ]:
                    request = first.model_copy(
                        update={"countermeasure_iri": "urn:fixture:" + suffix}
                    )
                    response = client.validate_countermeasure(request)
                    assert response.status == response.effective_status == expected
                    semantic.append(response.model_dump(mode="json", by_alias=True))
                # REST and MCP receive the same complete context and yield the same domain result.
                with httpx.Client(base_url=url, trust_env=False, timeout=15) as http:
                    body = {
                        "assetIri": first.asset_iri,
                        "countermeasureIri": first.countermeasure_iri,
                        "ontologyId": first.ontology_id,
                        "operationalContext": first.operational_context.model_dump(mode="json"),
                    }
                    rest = http.post("/api/v1/remediations/validate", json=body)
                    assert rest.status_code == 200, rest.text
                    mcp = client.validate_countermeasure(first)
                    assert rest.json()["operational"] == mcp.operational.model_dump(mode="json")
                    assert rest.json()["effectiveStatus"] == mcp.effective_status
                    body["assetIri"] = ":relative"
                    bad = http.post("/api/v1/remediations/validate", json=body)
                    assert bad.status_code == 400
                # Wrong CVE is rejected by SaaS using its actual stored ranking, before Tiny-ME.
                wrong = first.model_copy(deep=True)
                wrong.operational_context.cve_id = "CVE-2025-99999"
                try:
                    client.validate_countermeasure(wrong)
                except MCPToolError as exc:
                    assert exc.code == "INVALID_REQUEST"
                else:
                    raise AssertionError("Foreign ranking context accepted")
            (output / "mcp_events.jsonl").write_text("".join(json.dumps(e) + "\n" for e in events))
            report = {
                "success": True,
                "fabric": "simulated",
                "tiny_me": "simulated",
                "saas_and_stdio": "actual",
                "ledger_commit_verified": False,
                "cases": cases,
                "semantic": semantic,
                "rest_mcp_parity": True,
                "foreign_context_rejected": True,
                "relative_iri_rejected": True,
                "mcp_calls": len([e for e in events if e["event"] == "tool_call"]),
            }
            (output / "results.json").write_text(json.dumps(report, indent=2) + "\n")
            print(json.dumps({"success": True, "mcp_calls": report["mcp_calls"], "cases": cases}))
        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("node", "backend", "bridge", "prepared", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    smoke(**{key: value.resolve() for key, value in vars(args).items()})
