"""Prepara verifiche dagli artefatti validati, senza acquisire nuove evidenze."""

from thesis_agents.mcp.client import digest
from thesis_agents.schemas import RuntimeEvidence, VulnerabilityReport
from thesis_agents.schemas.verification import PackageVerificationContext, VerificationRequest


def package_verification_context(
    evidence: RuntimeEvidence, report: VulnerabilityReport
) -> PackageVerificationContext:
    package = report.package_assessment
    if package is None or evidence.telemetry is None:
        raise ValueError("Package verification requires Ubuntu evidence and telemetry")
    if (
        report.asset_id != evidence.service_name
        or package.observed_software != evidence.software[0]
    ):
        raise ValueError("Package verification inputs refer to different assets")
    groups = package.cve_ids_by_verdict
    potential, unknown = groups["potentially_affected"], groups["unknown"]
    pending = sorted(potential + unknown)
    requests = []

    def add(id_, kind, cves, required, pointers):
        if cves:
            requests.append(
                VerificationRequest(
                    id=id_,
                    kind=kind,
                    cve_ids=cves,
                    required_evidence=required,
                    source_pointers=pointers,
                )
            )

    add(
        "V_RUNTIME_STATE",
        "historical_runtime_state",
        pending,
        [
            "Recover package revision and running executable evidence contemporaneous with "
            "the recorded log window, including process start/restart times.",
            "Reconcile the later inventory timestamp with the recorded events; present-day "
            "observations cannot attest the historical process.",
        ],
        [
            "/package_assessment/historical_runtime_state",
            "/package_assessment/inventory_collected_at",
        ],
    )
    add(
        "V_RUNTIME_CONDITIONS",
        "runtime_conditions",
        potential,
        [
            "For each listed CVE, consult the linked assessment sources and obtain evidence "
            "for its specific affected modules, configuration and exploitation prerequisites.",
            "Establish loaded modules, effective configuration, reachable endpoints and "
            "exposure for the process and time under investigation. Missing data stays unknown.",
        ],
        [
            "/package_assessment/cve_ids_by_verdict/potentially_affected",
            "/package_assessment/response_file",
        ],
    )
    add(
        "V_UBUNTU_STATUS",
        "ubuntu_status",
        unknown,
        [
            "Investigate each listed CVE in the official Ubuntu sources for apache2 on bionic; "
            "record a release-specific status or preserve unknown with its reason.",
            "Retain source URL, content hash and status pointer; absence of a bionic entry "
            "does not establish fixed or not affected.",
        ],
        [
            "/package_assessment/cve_ids_by_verdict/unknown",
            "/package_assessment/source_manifest_sha256",
        ],
    )
    add(
        "V_UPGRADE_COMPATIBILITY",
        "upgrade_compatibility",
        potential,
        [
            "Identify a vendor-supported remediation path for the inventoried Ubuntu release "
            "and review all relevant advisories. A per-CVE fixed boundary is not a chosen target.",
            "Verify candidate package availability, dependencies, Apache module and application "
            "compatibility, maintenance capabilities, restart requirements and rollback plan "
            "before proposing a concrete upgrade version.",
        ],
        ["/package_assessment/inventory_version", "/package_assessment/response_file"],
    )
    return PackageVerificationContext(
        asset_id=evidence.service_name,
        runtime_evidence_id=evidence.software[0].evidence_id,
        runtime_evidence_sha256=digest(evidence.model_dump(mode="json")),
        vulnerability_report_sha256=digest(report.model_dump(mode="json")),
        package_response_sha256=package.response_sha256,
        verification_requests=requests,
        limitations=[
            "This context derives missing-evidence requests from published artifacts; "
            "it acquires no runtime, vendor or compatibility evidence.",
            "Requests are pending, unranked and unexecuted. They are not remediation strategies.",
            "Fixed and not-affected package CVEs are excluded from the pending investigation set.",
            "No concrete upgrade target, exploitation condition or vulnerability is confirmed.",
        ],
    )
