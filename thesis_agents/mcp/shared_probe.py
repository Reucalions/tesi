"""Handshake o singola chiamata tipizzata al bridge SaaS condiviso, senza LLM."""

import argparse
import json
import sys
from pathlib import Path

from dotenv import load_dotenv

from thesis_agents.mcp.shared_client import SharedMCPProfile, SharedServicesClient
from thesis_agents.mcp.shared_contracts import REQUESTS, shared_contracts


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", type=Path, required=True)
    parser.add_argument("--check-config", action="store_true")
    parser.add_argument("--tool", choices=tuple(REQUESTS))
    parser.add_argument("--request", type=Path)
    parser.add_argument(
        "--output-dir", type=Path, help="Directory nuova per audit, richiesta e risposta"
    )
    args = parser.parse_args(argv)
    try:
        load_dotenv(Path.cwd() / ".env", override=False)
        profile = SharedMCPProfile.load(args.profile)
        request = None
        if args.check_config:
            if args.tool or args.request:
                raise ValueError("--check-config esegue soltanto handshake e discovery")
        else:
            if not (args.tool and args.request and args.output_dir):
                raise ValueError("La chiamata richiede --tool, --request e --output-dir")
            request = REQUESTS[args.tool].model_validate_json(args.request.read_text())
        events = []
        if args.output_dir:
            args.output_dir.mkdir(parents=True, exist_ok=False)
            (args.output_dir / "profile.json").write_text(profile.model_dump_json(indent=2) + "\n")
            if request is not None:
                (args.output_dir / "request.json").write_text(
                    request.model_dump_json(indent=2) + "\n"
                )

        def audit(event):
            events.append(event)
            if args.output_dir:
                with (args.output_dir / "mcp_events.jsonl").open("a") as stream:
                    stream.write(json.dumps(event) + "\n")

        with SharedServicesClient(
            profile,
            audit=audit,
            stderr_path=args.output_dir / "mcp.stderr.log" if args.output_dir else None,
        ) as client:
            if args.check_config:
                result = {"server": client.client.server_info, "checked": list(shared_contracts())}
            elif args.tool in ("get_decision", "get_provenance"):
                result = getattr(client, args.tool)(request.decision_id).model_dump(
                    mode="json", by_alias=True, exclude_none=True
                )
            else:
                result = getattr(client, args.tool)(request).model_dump(
                    mode="json", by_alias=True, exclude_none=True
                )
        report = {"result": result, "mcp_events": events}
        if args.output_dir:
            (args.output_dir / "response.json").write_text(json.dumps(report, indent=2) + "\n")
        print(json.dumps(report, indent=2))
        return 0
    except (ValueError, OSError, RuntimeError) as exc:
        print(f"Errore MCP condiviso: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
