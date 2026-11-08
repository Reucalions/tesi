"""Collega il checkpoint canonico allo Strategic e al bridge SaaS condiviso via stdio."""

import argparse
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

from thesis_agents.mcp.shared_client import SharedMCPProfile, SharedServicesClient
from thesis_agents.strategic.contracts import NativeRankingSettings
from thesis_agents.strategic.session import NativeStrategicSession


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--prepared", required=True, type=Path)
    parser.add_argument("--mcp-profile", required=True, type=Path)
    parser.add_argument("--ranking-profile", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--mode", choices=("tool", "camel"), default="tool")
    args = parser.parse_args(argv)
    try:
        load_dotenv(Path.cwd() / ".env", override=False)
        profile = SharedMCPProfile.load(args.mcp_profile)
        settings = NativeRankingSettings.model_validate_json(args.ranking_profile.read_bytes())

        def audit(event):
            with (args.output / "mcp_events.jsonl").open("a") as stream:
                stream.write(json.dumps(event) + "\n")

        client = SharedServicesClient(
            profile, audit=audit, stderr_path=args.output / "mcp.stderr.log"
        )
        # Validation and new output directory precede process startup / remote writes.
        session = NativeStrategicSession(args.prepared, args.output, settings, client)
        with client:
            if args.mode == "camel":
                from thesis_agents.config import ModelSettings
                from thesis_agents.strategic.agent import run_native_strategic_agent

                result = run_native_strategic_agent(
                    session, ModelSettings.from_env().create_backend()
                )
            else:
                session.get_context()
                while operation := session.next_operation():
                    operation = dict(operation)
                    tool = operation.pop("tool")
                    getattr(session, tool)(**operation)
                result = session.assert_complete()
        print(result.model_dump_json(indent=2, by_alias=True))
        return 0
    except (ValueError, OSError, RuntimeError, ImportError) as exc:
        print(f"Strategic nativo fallito: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
