"""Collaudo isolato del resolver MCP; nessuna modifica al lookup della Workforce."""

import argparse
import json
from pathlib import Path

from thesis_agents.mcp.client import MCPClient, digest
from thesis_agents.mcp.cti_client import validate_response
from thesis_agents.mcp.cti_contracts import AssessmentRequest, SoftwareQuery
from thesis_agents.mcp.identity_contracts import (
    TOOL,
    IdentityEvidence,
    IdentityRequest,
    IdentityResolution,
)
from thesis_agents.mcp.identity_v2_contracts import IdentityResolution as IdentityResolutionV2
from thesis_agents.mcp.settings import MCPSettings
from thesis_agents.schemas.telemetry_source import TelemetrySnapshot
from thesis_agents.tools.telemetry_http import evidence_from_snapshot


def request_from_snapshot(snapshot: TelemetrySnapshot):
    evidence = evidence_from_snapshot(snapshot)
    context = snapshot.recorded_context
    row = snapshot.observations[0]
    if context is None or row.original_log is None:
        raise ValueError("Identity probe requires recorded Apache source binding")
    software = evidence.software[0]
    return IdentityRequest(
        evidence=IdentityEvidence(
            software=SoftwareQuery(
                product=software.package, version=software.version, evidence_id=software.evidence_id
            ),
            identity_basis=row.identity_basis,
            service=context.service,
            host=context.host,
            instance_basis=context.instance_basis,
            inventory_package=context.package_name,
            inventory_version=context.package_version,
            inventory_origin=context.package_origin,
            facts_collected_at=context.facts_collected_at,
            telemetry_snapshot_sha256=digest(snapshot.model_dump(mode="json")),
            export_sha256=snapshot.source_sha256,
            facts_sha256=context.facts_sha256,
            record_sha256=row.record_sha256,
            original_log_sha256=row.original_log.sha256,
            record_pointer=row.pointer,
        )
    )


def validate_identity(
    payload, request, expected_kind, expected_dataset_sha256=None, *, contract="v1"
):
    model = {"v1": IdentityResolution, "v2": IdentityResolutionV2}[contract]
    response = model.model_validate(payload)
    if response.request_sha256 != digest(request.model_dump(mode="json")):
        raise ValueError("Identity request hash differs")
    if response.evidence != request.evidence or response.backend_kind != expected_kind:
        raise ValueError("Identity response changed evidence or backend kind")
    if response.upstream_assessment is not None:
        raw = validate_response(
            response.upstream_assessment.model_dump(mode="json"),
            AssessmentRequest(software=response.normalized_query),
            expected_kind,
        )
        if expected_dataset_sha256 is not None and raw.dataset.sha256 != expected_dataset_sha256:
            raise ValueError("Identity dataset differs from configured snapshot")
    return response


def run_probe(settings, snapshot_path, output, *, expected_dataset_sha256=None, contract="v1"):
    raw = snapshot_path.read_bytes()
    snapshot = TelemetrySnapshot.model_validate_json(raw)
    request = request_from_snapshot(snapshot)
    output.mkdir(parents=True, exist_ok=False)
    (output / "telemetry_snapshot.json").write_bytes(raw)
    (output / "request.json").write_text(request.model_dump_json(indent=2) + "\n")
    events = []
    summary = {
        "status": "failed",
        "llm_used": False,
        "workforce_run": False,
        "mode": "cti-identity-probe",
        "endpoint": settings.url,
        "contract_version": contract,
    }
    try:
        model = {"v1": IdentityResolution, "v2": IdentityResolutionV2}[contract]
        contracts = {TOOL: (IdentityRequest.model_json_schema(), model.model_json_schema())}
        with MCPClient(settings, contracts=contracts, audit=events.append) as client:
            result = client.call_tool(
                TOOL,
                request.model_dump(mode="json"),
                lambda p: validate_identity(
                    p, request, settings.expected_kind, expected_dataset_sha256, contract=contract
                ),
            )
        (output / "identity_resolution.json").write_text(result.model_dump_json(indent=2) + "\n")
        summary.update(
            status="validated",
            identity_status=result.status,
            group_id=result.group_id,
            selected_identity_ids=result.selected_identity_ids,
            package_applicability=result.package_applicability,
            response_sha256=digest(result.model_dump(mode="json")),
            rule_sha256=result.rule_sha256,
        )
        if contract == "v2" and result.search is not None:
            summary["search_coverage"] = result.search.coverage.model_dump(mode="json")
            summary["candidate_counts"] = {
                disposition: sum(c.disposition == disposition for c in result.candidates)
                for disposition in ("equivalent", "excluded", "unresolved")
            }
        return result
    except Exception as error:
        summary["error_type"] = type(error).__name__
        raise
    finally:
        (output / "audit.json").write_text(json.dumps(events, indent=2) + "\n")
        (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", required=True)
    parser.add_argument("--snapshot", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--expected-kind", choices=("real", "mock"), required=True)
    parser.add_argument("--dataset-sha256")
    parser.add_argument("--contract", choices=("v1", "v2"), default="v1")
    args = parser.parse_args()
    result = run_probe(
        MCPSettings(url=args.url, expected_kind=args.expected_kind, timeout_seconds=60),
        args.snapshot,
        args.output_dir,
        expected_dataset_sha256=args.dataset_sha256,
        contract=args.contract,
    )
    print(f"Identity: {result.status}; package applicability: {result.package_applicability}.")


if __name__ == "__main__":
    main()
