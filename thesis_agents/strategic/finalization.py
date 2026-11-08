"""Register an archived, verified recommendation through the shared MCP backend."""

import argparse
import sys
from pathlib import Path

from thesis_agents.backends import RunAudit
from thesis_agents.mcp.shared_client import SharedMCPProfile, SharedServicesClient
from thesis_agents.strategic.finalization_session import (
    NativeFinalizationSession,
    load_selection_checkpoint,
)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selection-run", type=Path, required=True)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--mode", choices=("tool", "camel"), default="tool")
    args = parser.parse_args(argv)
    try:
        recommendation, _ = load_selection_checkpoint(args.selection_run)
        profile = SharedMCPProfile.load(args.profile)
        if profile.connection.expected_kind != recommendation.backend_kind or args.output.exists():
            raise ValueError("Backend kind differs or output already exists")
        # Audit begins after the guarded constructor creates the checkpoint directory.
        with SharedServicesClient(profile, finalization=True) as client:
            session = NativeFinalizationSession(args.selection_run, args.output, client)
            client.client.audit = RunAudit(
                args.output / "shared_mcp_events.jsonl", recommendation.run_id
            )
            if args.mode == "camel":
                from dotenv import load_dotenv

                from thesis_agents.config import ModelSettings
                from thesis_agents.strategic.finalization_agent import run_finalization_agent

                load_dotenv(Path.cwd() / ".env", override=False)
                result = run_finalization_agent(session, ModelSettings.from_env().create_backend())
            else:
                session.get_context()
                while operation := session.next_operation():
                    getattr(session, operation["tool"])()
                result = session.assert_complete()
        print(result.model_dump_json(indent=2, by_alias=True))
        return 0
    except (ValueError, OSError, RuntimeError, ImportError) as exc:
        print(f"Finalizzazione condivisa fallita: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
