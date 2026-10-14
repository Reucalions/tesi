"""Collaudo CAMEL dell'ingresso SBOM/OSV configurato, senza inferenza LLM."""

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from thesis_agents.backends import BackendSettings, connect_backends
from thesis_agents.orchestration.artifacts import ArtifactSession
from thesis_agents.orchestration.workforce import run_camel
from thesis_agents.schemas import RuntimeEvidence, StaticTelemetry, VulnerabilityReport
from thesis_agents.schemas.telemetry_source import TelemetryInput
from thesis_agents.telemetry.settings import TelemetryHTTPSettings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backends", type=Path, default=Path("config/backends.sbom-osv.json"))
    parser.add_argument("--input", type=Path, default=Path("thesis_agents/data/log4j_case.json"))
    parser.add_argument("--supply-chain-url")
    parser.add_argument("--cti-url")
    parser.add_argument("--telemetry-url")
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args()
    settings = json.loads(args.backends.read_text())
    if args.supply_chain_url:
        settings["countermeasure_input"]["url"] = args.supply_chain_url
    if args.cti_url:
        settings["vulnerability"]["url"] = args.cti_url
    if args.telemetry_url:
        settings["telemetry"]["url"] = args.telemetry_url
    config = BackendSettings.model_validate(settings)
    schema = (
        TelemetryInput if isinstance(config.telemetry, TelemetryHTTPSettings) else StaticTelemetry
    )
    case = schema.model_validate_json(args.input.read_text())
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from test_camel_integration import ScriptedToolModel

    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    output = args.output_dir or Path("output") / f"sbom-workforce-{stamp}-{uuid4().hex[:8]}"
    output.mkdir(parents=True, exist_ok=False)
    summary = {
        "status": "failed",
        "llm_used": False,
        "mode": "camel-sbom-scripted-smoke",
        "backends": config.model_dump(mode="json"),
    }
    try:
        session = ArtifactSession(case, output / "artifacts", model="scripted-test-only")
        model = ScriptedToolModel(session)
        with connect_backends(session, config):
            decision = run_camel(session, lambda: model)
        session.assert_complete()
        context = model.received_contexts["countermeasure"]
        extra = context["external_inputs"]["countermeasure"]["context"]
        assert extra == json.loads((session.output_dir / "countermeasure_context.json").read_text())
        strategic = model.received_contexts["strategic"]
        assert strategic["external_inputs"]["countermeasure"]["context"] == extra
        for name in ("runtime_evidence", "vulnerability_report", "candidate_strategies"):
            assert strategic["artifacts"][name] == json.loads(
                (session.output_dir / f"{name}.json").read_text()
            )
        for name, payload in (
            ("countermeasure_context_received", context),
            ("strategic_context", strategic),
        ):
            (output / f"{name}.json").write_text(json.dumps(payload, indent=2) + "\n")
        report = session.require("vulnerability_report", VulnerabilityReport)
        evidence = session.require("runtime_evidence", RuntimeEvidence)
        summary.update(
            status="validated",
            sbom_kind=extra["sbom_kind"],
            osv_kind=extra["osv_kind"],
            component=extra["component"],
            correlated_advisories=[a["id"] for a in extra["advisories"]],
            other_osv_ids=extra["other_osv_ids"],
            lookup_status=report.lookup_status,
            cti_backend_kind=report.cti.backend_kind if report.cti else "local-mock",
            decision_status=decision.status,
            telemetry_acquisition=evidence.telemetry.acquisition
            if evidence.telemetry
            else "static",
            runtime_software=[s.model_dump(mode="json") for s in evidence.software],
        )
    except Exception as error:
        summary["error_type"] = type(error).__name__
        raise
    finally:
        (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
        print(f"Evidenze SBOM/OSV (senza LLM): {output}")


if __name__ == "__main__":
    main()
