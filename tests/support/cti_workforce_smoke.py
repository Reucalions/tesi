"""Collaudo manuale CAMEL + servizio CTI separato, con inferenza programmata.

Non avvia backend né LLM e non legge il database. Usa cinque osservazioni di
test; le strategie prefissate verificano il flusso, non sono raccomandazioni
operative per le CVE restituite. Gli output restano separati dai run LLM.
"""

import argparse
import contextlib
import json
import sys
from datetime import UTC, datetime
from importlib.resources import files
from pathlib import Path
from uuid import uuid4

from thesis_agents.backends import BackendSettings, connect_backends
from thesis_agents.orchestration.artifacts import ArtifactSession
from thesis_agents.orchestration.workforce import run_camel
from thesis_agents.schemas import StaticTelemetry, VulnerabilityReport


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backends", type=Path, default=Path("config/backends.cti-real.json"))
    parser.add_argument("--url", help="Override esplicito dell'endpoint CTI per il collaudo")
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args(argv)
    config = json.loads(args.backends.read_text())
    if args.url:
        config["vulnerability"]["url"] = args.url
    settings = BackendSettings.model_validate(config)
    if settings.vulnerability_adapter != "cve2owl-v1":
        parser.error("Il collaudo richiede l'adapter cve2owl-v1")
    # Solo il runner di test importa il modello programmato; nessuna dipendenza
    # dai test entra nel client, nella CLI applicativa o nel servizio CTI.
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from test_camel_integration import ScriptedToolModel

    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    output = args.output_dir or Path("output") / f"cti-workforce-{stamp}-{uuid4().hex[:8]}"
    output.mkdir(parents=True, exist_ok=False)
    results = []
    cases = [
        ("runtime-package", "log4j-core", "2.14.1", "ambiguous", "insufficient_evidence"),
        ("canonical-log4j2", "Apache Log4j2", "2.14.1", "not_evaluable", "insufficient_evidence"),
        ("core-positive", "Apache Log4j Core", "2.14.1", "matched", "selected"),
        ("core-negative", "Apache Log4j Core", "2.25.4", "no_findings", "no_findings"),
        (
            "absent-product",
            "zzzzcostathesisabsent9f832c",
            "1.0",
            "no_match",
            "insufficient_evidence",
        ),
    ]
    for name, package, version, expected_lookup, expected_decision in cases:
        directory = output / name
        directory.mkdir()
        result = {"case": name, "status": "failed"}
        try:
            case = StaticTelemetry.model_validate_json(
                files("thesis_agents").joinpath("data/log4j_case.json").read_text()
            )
            case.package_name, case.package_version = package, version
            with (directory / "run.log").open("w") as log:
                with contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
                    session = ArtifactSession(
                        case, directory / "artifacts", mode="camel", model="scripted-test-only"
                    )
                    model = ScriptedToolModel(session)
                    with connect_backends(session, settings):
                        decision = run_camel(session, lambda backend=model: backend)
                    session.assert_complete()
                    report = session.require("vulnerability_report", VulnerabilityReport)
                    assert (report.lookup_status, decision.status) == (
                        expected_lookup,
                        expected_decision,
                    )
                    context = model.received_contexts["strategic"]
                    for artifact in (
                        "runtime_evidence",
                        "vulnerability_report",
                        "candidate_strategies",
                    ):
                        stored = json.loads((session.output_dir / f"{artifact}.json").read_text())
                        assert context["artifacts"][artifact] == stored
                    (directory / "strategic_context.json").write_text(
                        json.dumps(context, indent=2) + "\n"
                    )
                    result.update(
                        status="validated",
                        lookup_status=report.lookup_status,
                        decision_status=decision.status,
                        finding_ids=[f.cve_id for f in report.vulnerabilities],
                        identity_status=report.cti.identity_status,
                        rule_coverage=report.cti.rule_coverage,
                        dataset_sha256=report.cti.dataset_sha256,
                        backend_kind=report.cti.backend_kind,
                    )
        except Exception as error:
            result["error_type"] = type(error).__name__
        results.append(result)
        summary = {
            "mode": "camel-cti-scripted-smoke",
            "llm_used": False,
            "inference": "scripted-test-only",
            "backends": settings.model_dump(mode="json"),
            "cases": results,
            "status": "validated"
            if len(results) == len(cases) and all(r["status"] == "validated" for r in results)
            else "incomplete-or-failed",
        }
        (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
        print(f"{name}: {result['status']}", flush=True)
    print(f"Evidenze: {output}")
    return 0 if summary["status"] == "validated" else 1


if __name__ == "__main__":
    raise SystemExit(main())
