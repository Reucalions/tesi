"""Framework/stdio/HTTP/persistence are actual; Fabric and Tiny-ME are explicit fixtures."""

import argparse
import json
import os
import subprocess
import time
from pathlib import Path

import httpx

from thesis_agents.canonical.preparation import bytes_digest
from thesis_agents.canonical.session import load_prepared_checkpoint
from thesis_agents.mcp.operational_contracts import ACTION_REQUIREMENTS
from thesis_agents.mcp.shared_client import SharedMCPProfile, SharedServicesClient
from thesis_agents.strategic.contracts import NativeRankingSettings
from thesis_agents.strategic.finalization_session import NativeFinalizationSession
from thesis_agents.strategic.selection_session import NativeSelectionSession
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
    fixture_state = output / "backend-state"
    fixture_state.mkdir()
    environment = os.environ | {
        "SAAS_TEST_BACKEND": str(backend),
        "SAAS_TEST_STATE": str(fixture_state),
        "ARGUMENTATION_CHAINCODE": "argumentation",
        "SEMANTIC_CHAINCODE": "user-registry",
        "SEMANTIC_ONTOLOGY_KEY": "",
        "SAAS_TEST_SNAPSHOT_ID": preparation.knowledge_snapshot_id,
    }
    fixture = Path(__file__).with_name("saas_fixture.cjs")
    process = None
    log = (output / "backend.log").open("x")

    def start():
        ready = fixture_state / "ready.json"
        ready.unlink(missing_ok=True)
        proc = subprocess.Popen(
            [str(node), str(fixture)], cwd=backend, env=environment, stdout=log, stderr=log
        )
        for _ in range(200):
            if ready.exists():
                url = json.loads(ready.read_bytes())["url"]
                os.environ["FIN_SMOKE_URL"] = url
                return proc, url
            if proc.poll() is not None:
                raise RuntimeError("SaaS fixture startup failed; inspect backend.log")
            time.sleep(0.05)
        proc.terminate()
        proc.wait(timeout=5)
        raise TimeoutError("SaaS fixture did not start")

    def stop(proc):
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            proc.wait(timeout=5)

    events, cases, registered = [], [], []
    os.environ["FIN_SMOKE_USER"] = "fixture"
    profile = SharedMCPProfile.model_validate(
        {
            "connection": {
                "command": str(node),
                "args": [str(bridge / "build/index.js")],
                "cwd": str(bridge),
                "expected_kind": "real",
                "env_from": {"FABLO_REST_URL": "FIN_SMOKE_URL", "FABLO_USER": "FIN_SMOKE_USER"},
                "timeout_seconds": 15,
            }
        }
    )

    def connect(label):
        return SharedServicesClient(
            profile,
            finalization=True,
            audit=events.append,
            stderr_path=output / f"{label}.stderr.log",
        )

    try:
        process, url = start()
        (output / "mcp-profile.json").write_text(profile.model_dump_json(indent=2) + "\n")
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
        capabilities |= {cap for mapping in mappings for cap in mapping["required_capabilities"]}
        scenarios = [
            ("accepted", {}, "recommended"),
            ("alternative", {"prohibited_actions": ["upgrade"]}, "recommended"),
            ("missing", {"available_capabilities": []}, "requires_prerequisites"),
            ("review", {"constraint_mappings": []}, "requires_review"),
            ("rejected", {"prohibited_actions": list(ACTION_REQUIREMENTS)}, "no_valid_strategy"),
        ]
        with connect("main") as client:
            probe = client.rank_remediations(preparation.graphs[0].ranking_request)
            settings = NativeRankingSettings(
                tenant_id=probe.tenant_id,
                knowledge_snapshot_id=probe.knowledge_snapshot_id,
                knowledge_snapshot_digest=probe.knowledge_snapshot_digest,
                ontology_digest=probe.slsa_assurance.ontology_digest,
            )
            for name, update, expected in scenarios:
                root = output / name
                root.mkdir()
                native = NativeStrategicSession(prepared, root / "ranking", settings, client)
                ranking = finish(native)
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
                    policy_source="Explicit synthetic operator configuration",
                )
                validation = NativeValidationSession(
                    native.output_dir,
                    root / "validation",
                    ValidationProfile.model_validate(base | update),
                    client,
                )
                finish(validation)
                selection = NativeSelectionSession(validation.output_dir, root / "selection")
                recommendation = finish(selection)
                finalization = NativeFinalizationSession(
                    selection.output_dir, root / "finalization", client
                )
                result = finish(finalization)
                assert {r.record.document.recommendation.outcome for r in result.results} == {
                    expected
                }
                assert result.deployment_verified is False
                assert result.action_execution == "not_performed"
                for response in result.results:
                    document = response.record.document
                    assert document.recommendation == next(
                        r
                        for r in recommendation.results
                        if r.cve_id == document.recommendation.cve_id
                    )
                    assert client.finalize_recommendation(response.record.document_json) == response
                    registered.append(response)
                choice = result.results[0].record.document.recommendation.selected_strategy_id
                assert choice == (
                    "S_UPGRADE"
                    if name == "accepted"
                    else "S_ISOLATE"
                    if name == "alternative"
                    else None
                )
                cases.append(
                    {
                        "scenario": name,
                        "outcome": expected,
                        "selected_strategy_id": choice,
                        "records": len(result.results),
                        "idempotent_repeat": True,
                    }
                )
            original = registered[0]
            # Authenticated tenant and exact payload/parent are enforced at the HTTP boundary.
            path = f"/api/v1/decisions/{original.record.document.ranking_decision_id}/finalize"
            with httpx.Client(base_url=url, trust_env=False, timeout=15) as http:
                denied = http.post(
                    path,
                    headers={"x-tenant-id": "OtherMSP"},
                    json={"document_json": original.record.document_json},
                )
                assert denied.status_code == 403, denied.text
                changed = json.loads(original.record.document_json)
                changed["source_digests"]["native_strategic_recommendation"] = "sha256:" + "0" * 64
                conflict = http.post(path, json={"document_json": json.dumps(changed)})
                assert (
                    conflict.status_code == 409
                    and conflict.json()["error"] == "FINALIZATION_CONFLICT"
                ), conflict.text
                malformed = http.post(path, json={"document_json": '{"x":1,"x":2}'})
                assert malformed.status_code == 400
        stop(process)
        process = None
        calls_before = json.loads((fixture_state / "fabric-calls.json").read_bytes())
        before_writes = len([c for c in calls_before if c["method"] == "StoreRecommendation"])
        assert before_writes == len(registered)
        # Actual Node process restart: backend evidence and fixture ledger survive separately.
        process, _ = start()
        with connect("restart") as client:
            for original in registered:
                assert (
                    client.get_finalization(
                        original.record.document.ranking_decision_id,
                        original.record.finalization_id,
                    )
                    == original
                )
                assert client.finalize_recommendation(original.record.document_json) == original
        stop(process)
        process = None
        restart_calls = json.loads((fixture_state / "fabric-calls.json").read_bytes())
        assert not any(c["method"] == "StoreRecommendation" for c in restart_calls)
        report = {
            "success": True,
            "fabric": "simulated",
            "tiny_me": "simulated",
            "authentication": "simulated",
            "saas_http_stdio_framework": "actual",
            "backend_process_restart": True,
            "ledger_commit_independently_verified": False,
            "deployment_verified": False,
            "verification_scope": "backend_reported_commit_and_readback",
            "cases": cases,
            "stored_records": before_writes,
            "readbacks_after_restart": len(registered),
            "writes_after_restart": 0,
            "tenant_spoof_rejected": True,
            "changed_content_conflicts": True,
            "mcp_calls": len([e for e in events if e["event"] == "tool_call"]),
        }
        (output / "results.json").write_text(json.dumps(report, indent=2) + "\n")
        (output / "mcp_events.jsonl").write_text("".join(json.dumps(e) + "\n" for e in events))
        print(json.dumps(report))
    finally:
        if process is not None:
            stop(process)
        log.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("node", "backend", "bridge", "prepared", "output"):
        parser.add_argument("--" + name, type=Path, required=True)
    args = parser.parse_args()
    smoke(**{key: value.resolve() for key, value in vars(args).items()})
