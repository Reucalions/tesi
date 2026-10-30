"""Adapter Ubuntu: una chiamata MCP e una sintesi compatta, senza import del motore."""

from pathlib import Path

from thesis_agents.mcp.client import MCPClient, digest
from thesis_agents.mcp.ubuntu_contracts import TOOL, PackageAssessment, PackageRequest
from thesis_agents.mcp.ubuntu_probe import request_from_snapshot, validate_assessment
from thesis_agents.schemas import LookupResult, RuntimeEvidence
from thesis_agents.schemas.telemetry_source import TelemetrySnapshot
from thesis_agents.schemas.ubuntu import VERDICTS, UbuntuPackageEvidence
from thesis_agents.tools.telemetry_http import evidence_from_snapshot


def ubuntu_contracts():
    return {TOOL: (PackageRequest.model_json_schema(), PackageAssessment.model_json_schema())}


def map_ubuntu_assessment(response: PackageAssessment, snapshot: TelemetrySnapshot) -> LookupResult:
    request = request_from_snapshot(snapshot)
    validate_assessment(
        response.model_dump(mode="json"),
        request,
        response.backend_kind,
        dataset_sha256=response.source_identity_dataset_sha256,
        sources_sha256=response.source_manifest_sha256,
    )
    identity = response.identity_resolution
    summary = UbuntuPackageEvidence(
        backend_kind=response.backend_kind,
        observed_software=evidence_from_snapshot(snapshot).software[0],
        identity_status=identity.status,
        group_id=identity.group_id,
        selected_identity_ids=identity.selected_identity_ids,
        identity_candidate_counts={
            v: sum(c.disposition == v for c in identity.candidates)
            for v in ("equivalent", "excluded", "unresolved")
        },
        search_scope=identity.search.coverage.scope if identity.search else None,
        search_complete=identity.search.coverage.complete if identity.search else False,
        package_status=response.status,
        inventory_version=request.identity.evidence.inventory_version,
        inventory_collected_at=response.inventory.collected_at,
        facts_sha256=response.inventory.facts_sha256,
        inventory_matches=response.inventory_matches,
        source_scope_matches=response.source_scope_matches,
        scope=response.scope,
        runtime_applicability=response.runtime_applicability,
        historical_runtime_state=response.historical_runtime_state,
        cve_ids_by_verdict={
            v: [r.cve_id for r in response.results if r.verdict == v] for v in VERDICTS
        },
        counts=response.counts,
        dataset_sha256=response.source_identity_dataset_sha256,
        identity_rule_sha256=identity.rule_sha256,
        source_manifest_sha256=response.source_manifest_sha256,
        request_sha256=response.request_sha256,
        response_sha256=digest(response.model_dump(mode="json")),
        limitations=response.limitations
        + [
            "Original identity candidates, CVE sources and pointers remain in the linked snapshot.",
            "Package verdicts are separate from confirmed runtime vulnerabilities.",
        ],
    )
    return LookupResult(
        status=summary.lookup_status(), vulnerabilities=[], package_assessment=summary
    )


class UbuntuVulnerabilityTool:
    def __init__(self, client: MCPClient, output_dir: Path, *, dataset_sha256, sources_sha256):
        self.client, self.output_dir = client, output_dir
        self.dataset_sha256, self.sources_sha256 = dataset_sha256, sources_sha256

    def lookup_runtime_vulnerabilities(self, evidence, snapshot):
        if not isinstance(evidence, RuntimeEvidence) or evidence != evidence_from_snapshot(
            snapshot
        ):
            raise ValueError("Ubuntu lookup requires the exact published telemetry evidence")
        request = request_from_snapshot(snapshot)

        def parse(payload):
            response = validate_assessment(
                payload,
                request,
                self.client.settings.expected_kind,
                dataset_sha256=self.dataset_sha256,
                sources_sha256=self.sources_sha256,
            )
            result = map_ubuntu_assessment(response, snapshot)
            data = response.model_dump_json(indent=2) + "\n"
            path = self.output_dir / result.package_assessment.response_file
            if path.exists():
                if path.read_text() != data:
                    raise ValueError("Ubuntu snapshot is immutable within a run")
            else:
                with path.open("x", encoding="utf-8") as stream:
                    stream.write(data)
            return result

        return self.client.call_tool(TOOL, request.model_dump(mode="json"), parse)
