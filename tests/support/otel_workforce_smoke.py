"""Collaudo manuale OTEL -> CAMEL -> artefatti, con inferenza programmata."""

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from thesis_agents.backends import BackendSettings, connect_backends
from thesis_agents.orchestration.artifacts import ArtifactSession
from thesis_agents.orchestration.workforce import run_camel
from thesis_agents.schemas import RuntimeEvidence, VulnerabilityReport
from thesis_agents.schemas.telemetry_source import TelemetryInput


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, default=Path("config/input.otel-recorded.json"))
    parser.add_argument("--backends", type=Path, default=Path("config/backends.otel-recorded.json"))
    parser.add_argument("--telemetry-url")
    parser.add_argument("--cti-url")
    parser.add_argument("--output-dir", type=Path)
    args = parser.parse_args(argv)
    settings = json.loads(args.backends.read_text())
    if args.telemetry_url:
        settings["telemetry"]["url"] = args.telemetry_url
    if args.cti_url:
        settings["vulnerability"]["url"] = args.cti_url
    config = BackendSettings.model_validate(settings)
    case = TelemetryInput.model_validate_json(args.input.read_text())
    # Solo codice di collaudo: la CLI applicativa usa sempre il modello configurato.
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    from test_camel_integration import ScriptedToolModel

    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    output = args.output_dir or Path("output") / f"otel-workforce-{stamp}-{uuid4().hex[:8]}"
    output.mkdir(parents=True, exist_ok=False)
    summary = {
        "status": "failed",
        "mode": "camel-otel-scripted-smoke",
        "llm_used": False,
        "backends": config.model_dump(mode="json"),
    }
    try:
        session = ArtifactSession(
            case, output / "artifacts", mode="camel", model="scripted-test-only"
        )
        model = ScriptedToolModel(session)
        with connect_backends(session, config):
            decision = run_camel(session, lambda: model)
        session.assert_complete()
        context = model.received_contexts["strategic"]
        for artifact in ("runtime_evidence", "vulnerability_report", "candidate_strategies"):
            assert context["artifacts"][artifact] == json.loads(
                (session.output_dir / f"{artifact}.json").read_text()
            )
        (output / "strategic_context.json").write_text(json.dumps(context, indent=2) + "\n")
        evidence = session.require("runtime_evidence", RuntimeEvidence)
        report = session.require("vulnerability_report", VulnerabilityReport)
        summary.update(
            status="validated",
            acquisition=evidence.telemetry.acquisition,
            source_id=evidence.telemetry.source_id,
            source_sha256=evidence.telemetry.source_sha256,
            software=[s.model_dump(mode="json") for s in evidence.software],
            lookup_status=report.lookup_status,
            decision_status=decision.status,
            cti_backend_kind=report.cti.backend_kind if report.cti else None,
        )
    except Exception as error:
        summary["error_type"] = type(error).__name__
        raise
    finally:
        (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
        print(f"Evidenze del collaudo (senza LLM): {output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
