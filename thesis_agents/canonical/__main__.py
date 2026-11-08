"""Esegue il checkpoint semantico da tre artefatti MAS, senza avviare ranking o rete."""

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv

from thesis_agents.canonical.preparation import PreparationSettings
from thesis_agents.canonical.session import PreparationSession, load_request


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-run", required=True, type=Path)
    parser.add_argument("--request", required=True, type=Path)
    parser.add_argument("--profile", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--mode", choices=("tool", "camel"), default="tool")
    args = parser.parse_args(argv)
    try:
        session = PreparationSession(
            args.source_run,
            args.output,
            load_request(args.request),
            PreparationSettings.load(args.profile),
        )
        if args.mode == "camel":
            from thesis_agents.canonical.agent import run_preparation_agent
            from thesis_agents.config import ModelSettings

            load_dotenv(Path.cwd() / ".env", override=False)
            result = run_preparation_agent(session, ModelSettings.from_env().create_backend())
        else:
            session.prepare_argumentation()
            result = session.assert_complete()
        print(result.model_dump_json(indent=2, by_alias=True))
        return 0
    except (ValueError, OSError, RuntimeError, ImportError) as exc:
        print(f"Preparazione semantica fallita: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
