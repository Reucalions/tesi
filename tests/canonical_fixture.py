"""Dati sintetici espliciti per il checkpoint; nessuna pretesa di reasoning reale."""

import hashlib
import json
import sys
from pathlib import Path

from thesis_agents.canonical.contracts import PreparationRequest
from thesis_agents.canonical.preparation import PreparationSettings
from thesis_agents.fixtures import fixture_candidates, fixture_evidence
from thesis_agents.orchestration.artifacts import ArtifactSession
from thesis_agents.schemas import StaticTelemetry


def make_case(directory: Path, repository: Path):
    directory.mkdir(parents=True, exist_ok=True)
    case = StaticTelemetry(
        service_name="canonical-demo",
        package_name="log4j-core",
        package_version="2.14.1",
        endpoint_exposed=True,
        deserialization_observed=True,
        available_capabilities=[],
        prohibited_actions=[],
    )
    session = ArtifactSession(case, directory / "source-run", mode="fixtures")
    session.publish_runtime_evidence(fixture_evidence(session).model_dump_json())
    report = session.lookup_vulnerabilities()
    session.publish_vulnerability_report(json.dumps(report))
    cve = "CVE-2021-44228"
    candidates = fixture_candidates([cve])
    session.publish_candidate_strategies(candidates.model_dump_json())
    cna = cve + "_Containers_Cna"
    identifiers = [cna + f"_Solutions_{i}" for i in range(len(candidates.strategies))]
    axioms = [
        "Prefix(:=<urn:canonical-demo#>)",
        "Prefix(owl:=<http://www.w3.org/2002/07/owl#>)",
        "Ontology(<urn:canonical-demo>",
        f"ClassAssertion(:CveRecord :{cve})",
        f"ObjectPropertyAssertion(:hasContainers :{cve} :{cve}_Containers)",
        f"ObjectPropertyAssertion(:hasCna :{cve}_Containers :{cna})",
        f"ObjectPropertyAssertion(:hasAffected :{cna} :{cna}_Affected)",
        f"ObjectPropertyAssertion(:hasVersions :{cna}_Affected :{cna}_Version)",
        f'DataPropertyAssertion(:hasProduct :{cna}_Affected "log4j-core")',
        f'DataPropertyAssertion(:hasVendor :{cna}_Affected "apache")',
        f"ObjectPropertyAssertion(:hasMetrics :{cna} :{cna}_Metrics)",
        f"ObjectPropertyAssertion(:hasCvssV31 :{cna}_Metrics :{cna}_CVSS)",
    ]
    for role, value in [
        ("hasAttackVector", "AttackVectorNetwork"),
        ("hasAttackComplexity", "AttackComplexityLow"),
        ("hasPrivilegesRequired", "PrivilegesRequiredNone"),
        ("hasUserInteraction", "UserInteractionNone"),
        ("hasScope", "ScopeUnchanged"),
        ("hasConfidentialityImpact", "CIAImpactHigh"),
        ("hasIntegrityImpact", "CIAImpactHigh"),
        ("hasAvailabilityImpact", "CIAImpactHigh"),
        ("hasBaseSeverity", "SeverityCritical"),
    ]:
        axioms.append(f"ObjectPropertyAssertion(:{role} :{cna}_CVSS :{value})")
    axioms += [
        f"ObjectPropertyAssertion(:hasSolutions :{cna} :{identifier})" for identifier in identifiers
    ]
    axioms.append(")")
    ontology = directory / "source.owl"
    ontology.write_text("\n".join(axioms) + "\n")
    request = PreparationRequest.model_validate(
        {
            "run_id": session.run_id,
            "asset_id": case.service_name,
            "input_digests": {
                name: hashlib.sha256((session.output_dir / f"{name}.json").read_bytes()).hexdigest()
                for name in ("runtime_evidence", "vulnerability_report", "candidate_strategies")
            },
            "assessments": {
                "results": [
                    {
                        "asset": {"product": "log4j-core", "version": "2.14.1", "vendor": "apache"},
                        "matches": [
                            {
                                "confidence": "high",
                                "affected_entries": [
                                    {
                                        "cve_id": cve,
                                        "affected_iri": cna + "_Affected",
                                        "vulnerability_status": "vulnerable",
                                        "version_rules": [
                                            {
                                                "evaluated": True,
                                                "matched_asset_version": True,
                                                "vulnerability_status": "vulnerable",
                                                "version_iri": cna + "_Version",
                                            }
                                        ],
                                    }
                                ],
                            }
                        ],
                    }
                ]
            },
            "bindings": [
                {"cve_id": cve, "strategy_id": candidate.id, "ontology_individual": identifier}
                for candidate, identifier in zip(candidates.strategies, identifiers, strict=True)
            ],
        }
    )
    settings = PreparationSettings(
        repository=repository.resolve(),
        python=Path(sys.executable).absolute(),
        source_ontology=ontology.resolve(),
        source_ontology_sha256=hashlib.sha256(ontology.read_bytes()).hexdigest(),
        generator_manifest_sha256=hashlib.sha256(
            (repository / "app/semantic_preparation/installation-manifest.json").read_bytes()
        ).hexdigest(),
        knowledge_snapshot_id="urn:inspection:canonical-fixture",
        timeout_seconds=10,
    )
    return session.output_dir, request, settings
