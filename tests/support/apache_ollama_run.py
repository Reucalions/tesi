"""Prova effettiva CLI/CAMEL su Apache, con inferenza solo Ollama locale."""

import argparse
import os
import platform
import sys
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path

import httpx

from thesis_agents.demo import execute, local_model_info, source_hashes, write_json
from thesis_agents.demo_audit import sha256


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--model", default="tesi-apache-qwen3:4b-32k")
    parser.add_argument("--context-tokens", default=32768, type=int)
    parser.add_argument("--max-tokens", default=8192, type=int)
    parser.add_argument("--timeout", default=1800, type=int)
    args = parser.parse_args()
    run = args.output.resolve()
    run.mkdir(parents=True, exist_ok=False)
    root = Path(__file__).resolve().parents[2]
    profile = root / "config/backends.otel-apache-strategic.json"
    case = root / "config/input.otel-apache-recorded.json"
    info = local_model_info(args.model)
    with httpx.Client(base_url="http://127.0.0.1:11434", trust_env=False, timeout=10) as client:
        show = client.post("/api/show", json={"model": args.model}).raise_for_status().json()
        ollama_version = client.get("/api/version").raise_for_status().json()
        before = client.get("/api/ps").raise_for_status().json()
    write_json(run / "ollama-model.json", show)
    write_json(run / "ollama-before.json", before)
    hashes = source_hashes()
    hashes.update(
        {
            str(p.relative_to(root)): sha256(p)
            for p in (
                profile,
                case,
                Path(__file__).resolve(),
                *sorted((root / "services").rglob("*.py")),
            )
        }
    )
    for name in hashes:
        snapshot = run / "source-snapshot" / name
        snapshot.parent.mkdir(parents=True, exist_ok=True)
        snapshot.write_bytes((root / name).read_bytes())
    command = [
        sys.executable,
        "-u",
        "-m",
        "thesis_agents.main",
        "--mode",
        "camel",
        "--workflow",
        "pipeline",
        "--backends",
        str(profile),
        "--input",
        str(case),
        "--output",
        str(run / "artifacts"),
    ]
    write_json(
        run / "manifest.json",
        {
            "created_at": datetime.now(UTC).isoformat(),
            "llm_used": True,
            "model": args.model,
            "ollama_model": info,
            "ollama_version": ollama_version,
            "base_url": "http://127.0.0.1:11434/v1",
            "temperature": 0,
            "context_tokens": args.context_tokens,
            "max_tokens": args.max_tokens,
            "backend_timeout_seconds": 300,
            "process_timeout_seconds": args.timeout,
            "source_hashes": hashes,
            "reuse_recorded_sources": True,
            "new_agent_session": True,
            "python": platform.python_version(),
            "packages": {p: version(p) for p in ("camel-ai", "pydantic", "openai", "mcp")},
        },
    )
    write_json(run / "command.json", command)
    env = os.environ.copy()
    env.update(
        LLM_MODEL=args.model,
        LLM_API_KEY="local",
        OPENAI_API_KEY="local",
        LLM_BASE_URL="http://127.0.0.1:11434/v1",
        LLM_TEMPERATURE="0",
        LLM_TIMEOUT_SECONDS="300",
        LLM_MAX_TOKENS=str(args.max_tokens),
        LLM_CONTEXT_TOKENS=str(args.context_tokens),
        CAMEL_MODEL_LOG_ENABLED="true",
        CAMEL_LOG_DIR=str(run / "llm"),
    )
    write_json(run / "execution.json", {"execution_status": "running"})
    print(f"Inferenza Ollama effettiva: {run}", flush=True)
    execution = execute(command, run=run, env=env, timeout=args.timeout)
    execution["source_code_unchanged"] = all(sha256(root / p) == h for p, h in hashes.items())
    write_json(run / "execution.json", execution)
    with httpx.Client(base_url="http://127.0.0.1:11434", trust_env=False, timeout=10) as client:
        write_json(run / "ollama-after.json", client.get("/api/ps").raise_for_status().json())
    print(execution, flush=True)
    return execution["exit_code"]


if __name__ == "__main__":
    raise SystemExit(main())
