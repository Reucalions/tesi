"""Publish a native dry-run recommendation from a complete archived validation."""

import argparse
import sys
from pathlib import Path

from thesis_agents.strategic.selection_session import NativeSelectionSession


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--validation-run", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--mode", choices=("tool", "camel"), default="tool")
    args = parser.parse_args(argv)
    try:
        session = NativeSelectionSession(args.validation_run, args.output)
        if args.mode == "camel":
            from dotenv import load_dotenv

            from thesis_agents.config import ModelSettings
            from thesis_agents.strategic.selection_agent import run_selection_agent

            load_dotenv(Path.cwd() / ".env", override=False)
            result = run_selection_agent(session, ModelSettings.from_env().create_backend())
        else:
            session.get_context()
            session.publish_native_recommendation()
            result = session.assert_complete()
        print(result.model_dump_json(indent=2, by_alias=True))
        return 0
    except (ValueError, OSError, RuntimeError, ImportError) as exc:
        print(f"Selezione nativa fallita: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
