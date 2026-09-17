"""Runner riproducibile della demo: python -m thesis_agents.demo.

Avvia la CLI esistente in processi separati, conserva anche i fallimenti e
controlla i risultati senza pubblicare artefatti al posto degli agenti.
"""

import argparse
import json
import os
import platform
import shlex
import subprocess
import sys
import time
from datetime import UTC, datetime
from importlib.metadata import version
from pathlib import Path
from urllib.request import ProxyHandler, build_opener
from uuid import uuid4

from thesis_agents.demo_audit import audit_run, scenario_matches, sha256
from thesis_agents.schemas import StaticTelemetry

PACKAGE = Path(__file__).resolve().parent
SCENARIOS = tuple(p.stem for p in sorted((PACKAGE / "data").glob("demo_*.json")))
OLLAMA_URL = "http://localhost:11434"


def _positive(value):
    number = int(value)
    if number <= 0:
        raise argparse.ArgumentTypeError("Serve un intero positivo")
    return number


def write_json(path: Path, value):
    # Sostituzione atomica del solo riepilogo, mai degli artefatti di dominio.
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n")
    temporary.replace(path)


def source_hashes():
    paths = [*PACKAGE.rglob("*.py"), *(PACKAGE / "data").glob("*.json")]
    paths += [
        p
        for p in (PACKAGE.parent / "pyproject.toml", PACKAGE.parent / "requirements.lock")
        if p.exists()
    ]
    return {str(p.relative_to(PACKAGE.parent)): sha256(p) for p in sorted(paths)}


def local_model_info(model: str):
    # Endpoint locale fisso; niente proxy, download o credenziali dal file .env.
    opener = build_opener(ProxyHandler({}))
    with opener.open(f"{OLLAMA_URL}/api/tags", timeout=5) as response:
        installed = json.load(response)["models"]
    found = next((m for m in installed if m["name"] == model), None)
    if found is None:
        raise ValueError(f"Modello {model!r} non installato in Ollama locale")
    if found.get("remote_host") or found.get("remote_model") or model.endswith(":cloud"):
        raise ValueError("La demo richiede un modello installato per inferenza locale")
    return found


def child_environment(run: Path, model: str):
    env = os.environ.copy()
    env.update(
        LLM_MODEL=model,
        LLM_API_KEY="local",
        OPENAI_API_KEY="local",
        LLM_BASE_URL=f"{OLLAMA_URL}/v1",
        LLM_TIMEOUT_SECONDS="300",
        LLM_TEMPERATURE="0",
        LLM_MAX_TOKENS="2048",
        CAMEL_MODEL_LOG_ENABLED="true",
        CAMEL_LOG_DIR=str(run / "llm"),
    )
    return env


def execute(command, *, run: Path, env: dict, timeout: int):
    """Un processo per run: timeout e interruzioni conservano i risultati parziali."""
    start = time.monotonic()
    with (run / "run.log").open("w") as log:
        try:
            completed = subprocess.run(
                command,
                cwd=PACKAGE.parent,
                env=env,
                stdout=log,
                stderr=subprocess.STDOUT,
                timeout=timeout,
                check=False,
            )
            code = completed.returncode
            status = "completed" if code == 0 else "failed"
        except subprocess.TimeoutExpired:
            code, status = 124, "timeout"
        except KeyboardInterrupt:
            code, status = 130, "interrupted"
        except OSError as exc:
            log.write(str(exc) + "\n")
            code, status = 1, "failed"
    return {
        "exit_code": code,
        "execution_status": status,
        "elapsed_seconds": round(time.monotonic() - start, 2),
    }


def write_summary(batch: Path, manifest: dict, runs: list, *, state: str, errors: list):
    summary = {
        "state": state,
        "planned_runs": manifest["planned_runs"],
        "finished_runs": len(runs),
        "verified_runs": sum(r["verified"] for r in runs),
        "errors": errors,
        "runs": runs,
    }
    write_json(batch / "summary.json", summary)
    rows = [
        "# Riepilogo demo",
        "",
        f"Stato batch: **{state}**. "
        f"Run verificati: {summary['verified_runs']}/{manifest['planned_runs']}.",
        "",
        "| Run | Processo | Decisione | Strategia | Secondi | Richieste LLM | Verificato |",
        "|---|---|---|---|---:|---:|---|",
    ]
    for run in runs:
        audit = run["audit"]
        rows.append(
            f"| [{run['name']}]({run['name']}/run_summary.json) | "
            f"{run['execution_status']} | {audit.get('decision_status', '—')} | "
            f"{audit.get('selected_strategy_id') or '—'} | {run['elapsed_seconds']} | "
            f"{audit['llm_requests']} | {'sì' if run['verified'] else 'no'} |"
        )
    rows += [
        "",
        "Il commento LLM resta non verificato. I controlli riguardano i contratti",
        "e i mock configurati, non l'efficacia delle contromisure nel mondo reale.",
    ]
    if errors:
        rows += ["", *[f"- {error}" for error in errors]]
    (batch / "summary.md").write_text("\n".join(rows) + "\n")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Matrice demo CAMEL/Ollama o fixture senza LLM")
    parser.add_argument("--mode", choices=("camel", "fixtures"), default="camel")
    parser.add_argument("--scenarios", nargs="+", choices=SCENARIOS, default=list(SCENARIOS))
    parser.add_argument("--repetitions", type=_positive, default=2)
    parser.add_argument("--model", default="tesi-qwen3:4b")
    parser.add_argument(
        "--timeout", type=_positive, default=300, help="Limite secondi per processo"
    )
    parser.add_argument(
        "--output", type=Path, help="Directory nuova; default output/demo-matrix-..."
    )
    args = parser.parse_args(argv)
    try:
        # Rifiuta subito il riuso di una cartella: nessuna prova storica è sovrascritta.
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        batch = (args.output or Path("output") / f"demo-matrix-{stamp}-{uuid4().hex[:8]}").resolve()
        if batch.exists():
            raise ValueError(f"La directory deve essere nuova: {batch}")
        model_info = local_model_info(args.model) if args.mode == "camel" else None
        scenarios = list(dict.fromkeys(args.scenarios))
        inputs = {
            name: StaticTelemetry.model_validate_json(
                (PACKAGE / "data" / f"{name}.json").read_text()
            )
            for name in scenarios
        }
        hashes = source_hashes()
        batch.mkdir(parents=True)
        (batch / "inputs").mkdir()
        for name, case in inputs.items():
            write_json(batch / "inputs" / f"{name}.json", case.model_dump(mode="json"))
        manifest = {
            "created_at": datetime.now(UTC).isoformat(),
            "mode": args.mode,
            "workflow": "pipeline",
            "model": args.model if model_info else None,
            "ollama_model": model_info,
            "base_url": f"{OLLAMA_URL}/v1" if model_info else None,
            "temperature": 0 if model_info else None,
            "max_tokens": 2048 if model_info else None,
            "backend_timeout_seconds": 300 if model_info else None,
            "process_timeout_seconds": args.timeout,
            "repetitions": args.repetitions,
            "scenarios": scenarios,
            "planned_runs": len(scenarios) * args.repetitions,
            "python": platform.python_version(),
            "platform": platform.platform(),
            "packages": {name: version(name) for name in ("camel-ai", "pydantic", "openai")},
            "source_hashes": hashes,
            "input_hashes": {name: sha256(batch / "inputs" / f"{name}.json") for name in scenarios},
            "runner_command": [
                sys.executable,
                "-m",
                "thesis_agents.demo",
                *(argv if argv is not None else sys.argv[1:]),
            ],
        }
        write_json(batch / "manifest.json", manifest)
        print(f"Batch: {batch}", flush=True)
        runs, errors = [], []
        write_summary(batch, manifest, runs, state="running", errors=errors)
        for repetition in range(1, args.repetitions + 1):
            for scenario in scenarios:
                if source_hashes() != hashes:
                    errors.append("Sorgenti cambiati durante la matrice; esecuzione interrotta")
                    break
                run = batch / f"{scenario}-r{repetition}"
                run.mkdir()
                command = [
                    sys.executable,
                    "-u",
                    "-m",
                    "thesis_agents.main",
                    "--mode",
                    args.mode,
                    "--workflow",
                    "pipeline",
                    "--input",
                    str(batch / "inputs" / f"{scenario}.json"),
                    "--output",
                    str(run / "artifacts"),
                ]
                write_json(run / "command.json", command)
                (run / "command.txt").write_text(shlex.join(command) + "\n")
                print(f"Avvio {run.name}", flush=True)
                record = {
                    "name": run.name,
                    "scenario": scenario,
                    "repetition": repetition,
                    **execute(
                        command,
                        run=run,
                        env=child_environment(run, args.model),
                        timeout=args.timeout,
                    ),
                }
                record["audit"] = audit_run(
                    run, inputs[scenario], mode=args.mode, model=args.model if model_info else None
                )
                record["scenario_matches"] = scenario_matches(scenario, record["audit"])
                record["sources_unchanged"] = source_hashes() == hashes
                record["verified"] = (
                    record["exit_code"] == 0
                    and record["audit"]["passed"]
                    and record["scenario_matches"]
                    and record["sources_unchanged"]
                )
                write_json(run / "run_summary.json", record)
                runs.append(record)
                write_summary(batch, manifest, runs, state="running", errors=errors)
                print(
                    f"Fine {run.name}: {record['execution_status']}, "
                    f"{record['elapsed_seconds']}s, verificato={record['verified']}",
                    flush=True,
                )
                if record["execution_status"] == "interrupted":
                    errors.append("Interruzione richiesta; run parziale conservato")
                    break
            if errors:
                break
        if model_info:
            try:
                if local_model_info(args.model).get("digest") != model_info.get("digest"):
                    errors.append("Il modello Ollama è cambiato durante la matrice")
            except (OSError, ValueError) as exc:
                errors.append(f"Verifica finale Ollama: {exc}")
        complete = (
            not errors
            and len(runs) == manifest["planned_runs"]
            and all(r["verified"] for r in runs)
        )
        write_summary(
            batch, manifest, runs, state="passed" if complete else "failed", errors=errors
        )
        print(f"Risultati: {batch / 'summary.md'}", flush=True)
        return 0 if complete else 1
    except (OSError, ValueError) as exc:
        print(f"Errore demo: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
