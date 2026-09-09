import argparse
import json
import sys
from datetime import UTC, datetime
from importlib.resources import files
from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv

from thesis_agents.config import ModelSettings
from thesis_agents.orchestration.artifacts import ARTIFACT_SCHEMAS, ArtifactSession
from thesis_agents.schemas import StaticTelemetry


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Prototipo CAMEL per il caso Log4j")
    parser.add_argument("--mode", choices=("camel", "fixtures"), default="camel")
    parser.add_argument("--workflow", choices=("pipeline", "auto"), default="pipeline")
    parser.add_argument(
        "--input", type=Path, help="JSON StaticTelemetry; default: caso Log4j incluso"
    )
    parser.add_argument(
        "--output", type=Path, help="Cartella vuota; default: output/<timestamp>-<id>"
    )
    parser.add_argument(
        "--export-schemas", type=Path, help="Esporta JSON Schema senza eseguire agenti"
    )
    args = parser.parse_args(argv)
    try:
        if args.export_schemas:
            args.export_schemas.mkdir(parents=True, exist_ok=True)
            schemas = {"input": StaticTelemetry, **ARTIFACT_SCHEMAS}
            for name, schema in schemas.items():
                path = args.export_schemas / f"{name}.schema.json"
                with path.open("x", encoding="utf-8") as stream:
                    json.dump(schema.model_json_schema(), stream, indent=2)
                    stream.write("\n")
            print(f"Schemi esportati: {args.export_schemas.resolve()}")
            return 0
        # Explicit project-local file; never search parent folders for credentials.
        load_dotenv(Path.cwd() / ".env", override=False)
        settings = ModelSettings.from_env() if args.mode == "camel" else None
        content = (
            args.input.read_text()
            if args.input
            else (files("thesis_agents").joinpath("data/log4j_case.json").read_text())
        )
        case = StaticTelemetry.model_validate_json(content)
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        output = args.output or Path("output") / f"{stamp}-{uuid4().hex[:8]}"
        session = ArtifactSession(
            case, output, mode=args.mode, model=settings.model if settings else None
        )
        print(f"Modalità: {args.mode} | Output: {output.resolve()}", flush=True)
        if settings:
            from thesis_agents.orchestration.workforce import run_camel

            decision = run_camel(session, settings.create_backend, workflow=args.workflow)
        else:
            from thesis_agents.fixtures import run_fixtures

            decision = run_fixtures(session)
        print(f"Esito: {decision.status}; strategia: {decision.selected_strategy_id or 'nessuna'}")
        print("Creati gli 8 artefatti JSON e la copia dell’input.")
        return 0
    except (ValueError, OSError, RuntimeError, ImportError) as exc:
        print(f"Errore: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
