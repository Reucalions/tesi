"""Collaudo MCP isolato: applicabilità Ubuntu dell'inventario, nessun finding runtime."""

import argparse
import json
from pathlib import Path

from thesis_agents.mcp.client import MCPClient, digest
from thesis_agents.mcp.identity_probe import request_from_snapshot as identity_request
from thesis_agents.mcp.identity_probe import validate_identity
from thesis_agents.mcp.settings import MCPSettings
from thesis_agents.mcp.ubuntu_contracts import TOOL, PackageAssessment, PackageRequest
from thesis_agents.schemas.telemetry_source import TelemetrySnapshot


def request_from_snapshot(snapshot):
    context = snapshot.recorded_context
    if context is None:
        raise ValueError("Ubuntu probe requires recorded inventory context")
    return PackageRequest(
        identity=identity_request(snapshot),
        distribution=context.distribution,
        release=context.distribution_release,
        release_version=context.distribution_version,
    )


def validate_assessment(payload, request, expected_kind, *, dataset_sha256, sources_sha256):
    result = PackageAssessment.model_validate(payload)
    if result.request != request or result.request_sha256 != digest(
        request.model_dump(mode="json")
    ):
        raise ValueError("Ubuntu package request/evidence differs")
    if result.backend_kind != expected_kind or result.source_manifest_sha256 != sources_sha256:
        raise ValueError("Ubuntu backend or pinned sources differ")
    validate_identity(
        result.identity_resolution.model_dump(mode="json"),
        request.identity,
        expected_kind,
        dataset_sha256,
        contract="v2",
    )
    return result


def run_probe(settings, snapshot_path, output, *, dataset_sha256, sources_sha256):
    raw = snapshot_path.read_bytes()
    request = request_from_snapshot(TelemetrySnapshot.model_validate_json(raw))
    output.mkdir(parents=True, exist_ok=False)
    (output / "telemetry_snapshot.json").write_bytes(raw)
    (output / "request.json").write_text(request.model_dump_json(indent=2) + "\n")
    events = []
    summary = {
        "status": "failed",
        "mode": "ubuntu-package-probe",
        "llm_used": False,
        "workforce_run": False,
        "endpoint": settings.url,
    }
    try:
        contracts = {
            TOOL: (PackageRequest.model_json_schema(), PackageAssessment.model_json_schema())
        }
        with MCPClient(settings, contracts=contracts, audit=events.append) as client:
            result = client.call_tool(
                TOOL,
                request.model_dump(mode="json"),
                lambda payload: validate_assessment(
                    payload,
                    request,
                    settings.expected_kind,
                    dataset_sha256=dataset_sha256,
                    sources_sha256=sources_sha256,
                ),
            )
        (output / "package_assessment.json").write_text(result.model_dump_json(indent=2) + "\n")
        summary.update(
            status="validated",
            package_status=result.status,
            counts=result.counts,
            inventory_version=request.identity.evidence.inventory_version,
            source_manifest_sha256=result.source_manifest_sha256,
            response_sha256=digest(result.model_dump(mode="json")),
            runtime_applicability=result.runtime_applicability,
            historical_runtime_state=result.historical_runtime_state,
        )
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
    parser.add_argument("--dataset-sha256", required=True)
    parser.add_argument("--sources-sha256", required=True)
    args = parser.parse_args()
    result = run_probe(
        MCPSettings(url=args.url, expected_kind=args.expected_kind, timeout_seconds=60),
        args.snapshot,
        args.output_dir,
        dataset_sha256=args.dataset_sha256,
        sources_sha256=args.sources_sha256,
    )
    print(
        f"Package: {result.status}; counts: {result.counts}; "
        f"runtime: {result.runtime_applicability}."
    )


if __name__ == "__main__":
    main()
