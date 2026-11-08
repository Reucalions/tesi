"""Valida un ranking canonico salvato con IRI e policy operativa espliciti."""

import argparse
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

from thesis_agents.mcp.shared_client import SharedMCPProfile, SharedServicesClient
from thesis_agents.strategic.validation_contracts import ValidationProfile
from thesis_agents.strategic.validation_session import NativeValidationSession


def execute_validation(session, mode):
    if mode == "camel":
        from thesis_agents.config import ModelSettings
        from thesis_agents.strategic.validation_agent import run_validation_agent

        return run_validation_agent(session, ModelSettings.from_env().create_backend())
    session.get_context()
    while operation := session.next_operation():
        arguments = dict(operation)
        getattr(session, arguments.pop("tool"))(**arguments)
    return session.assert_complete()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ranking-run", type=Path, required=True)
    parser.add_argument("--validation-profile", type=Path, required=True)
    parser.add_argument("--mcp-profile", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--mode", choices=("tool", "camel"), default="tool")
    args = parser.parse_args(argv)
    try:
        load_dotenv(Path.cwd() / ".env", override=False)
        profile = ValidationProfile.model_validate_json(args.validation_profile.read_bytes())

        def audit(event):
            with (args.output / "mcp_events.jsonl").open("a") as stream:
                stream.write(json.dumps(event) + "\n")

        client = SharedServicesClient(
            SharedMCPProfile.load(args.mcp_profile),
            audit=audit,
            stderr_path=args.output / "mcp.stderr.log",
        )
        session = NativeValidationSession(args.ranking_run, args.output, profile, client)
        with client:
            result = execute_validation(session, args.mode)
        print(result.model_dump_json(indent=2, by_alias=True))
        return 0
    except (ValueError, OSError, RuntimeError, ImportError) as exc:
        print(f"Validazione nativa fallita: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
