"""Collaudo opt-in con la copia esterna del backend e il client CLI di tesi.

Usa esclusivamente il database sintetico della suite del backend. I suoi moduli
vengono caricati solo nei sottoprocessi di preparazione fixture e server.
Non è un test della Workforce né una validazione su dati CTI reali.
"""

import argparse
import json
import os
import socket
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

import httpx


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--backend-root", type=Path, required=True)
    args = parser.parse_args()
    backend = args.backend_root.resolve(strict=True)
    project = Path(__file__).resolve().parents[2]
    fixture = backend / "app/tests/cti_mcp/conftest.py"
    if not fixture.is_file():
        parser.error("Il backend deve includere la suite cti_mcp")
    output = (
        project / "output" / (f"cti-mcp-smoke-{datetime.now(UTC):%Y%m%dT%H%M%SZ}-{uuid4().hex[:8]}")
    )
    output.mkdir(parents=True)
    backend_env = {**os.environ, "PYTHONPATH": str(backend / "app/src")}
    subprocess.run(
        [
            sys.executable,
            "-c",
            "import runpy,sys; from pathlib import Path; "
            "runpy.run_path(sys.argv[1])['index'].__wrapped__(Path(sys.argv[2]))",
            str(fixture),
            str(output),
        ],
        env=backend_env,
        cwd=backend,
        check=True,
        timeout=10,
    )
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    url = f"http://127.0.0.1:{port}/mcp"
    command = [
        sys.executable,
        "-m",
        "cti_mcp.server",
        "--sqlite",
        str(output / "synthetic.affected.sqlite"),
        "--dataset-id",
        "synthetic-interoperability-v1",
        "--dataset-kind",
        "fixture",
        "--port",
        str(port),
    ]
    summary = {"dataset_kind": "fixture", "llm_used": False, "server_command": command, "runs": []}
    scenarios = [
        ("vulnerable", "Demo Library", "1.5", "mock", 0, "vulnerable"),
        ("outside-range", "Demo Library", "2.0", "mock", 0, "not_vulnerable"),
        ("unknown-version", "Demo Library", "unknown", "mock", 0, "not_evaluable"),
        ("missing-product", "zzzzunrelatedpackage", "1.5", "mock", 0, None),
        ("ambiguous-product", "Ambiguous Widget", "1.5", "mock", 0, "vulnerable"),
        ("wrong-kind", "Demo Library", "1.5", "real", 1, None),
    ]
    with (output / "server.log").open("w") as log:
        process = subprocess.Popen(command, env=backend_env, cwd=backend, stdout=log, stderr=log)
        try:
            with httpx.Client(timeout=0.2, trust_env=False) as http:
                deadline = time.monotonic() + 10
                while True:
                    if process.poll() is not None:
                        raise RuntimeError(
                            "Server terminato durante l'avvio; consultare server.log"
                        )
                    try:
                        http.get(url)
                        break
                    except httpx.HTTPError:
                        if time.monotonic() >= deadline:
                            raise TimeoutError("Avvio server") from None
                        time.sleep(0.02)
            for name, product, version, kind, expected_code, expected_status in scenarios:
                run_dir = output / name
                client_command = [
                    sys.executable,
                    "-m",
                    "thesis_agents.mcp.cti_probe",
                    "--url",
                    url,
                    "--expected-kind",
                    kind,
                    "--product",
                    product,
                    "--version",
                    version,
                    "--evidence-id",
                    f"fixture-{name}",
                    "--output-dir",
                    str(run_dir),
                ]
                result = subprocess.run(
                    client_command, cwd=project, capture_output=True, text=True, timeout=30
                )
                (output / f"{name}.log").write_text(result.stdout + result.stderr)
                summary["runs"].append(
                    {"name": name, "command": client_command, "returncode": result.returncode}
                )
                assert result.returncode == expected_code, f"Unexpected exit: {name}"
                if expected_code:
                    assert not (run_dir / "assessment.json").exists()
                    continue
                response = json.loads((run_dir / "assessment.json").read_text())
                assert response["dataset"]["kind"] == "fixture"
                assessments = response["assessment"]["results"]
                if expected_status is None:
                    assert assessments == []
                else:
                    assert assessments[0]["matches"][0]["vulnerability_status"] == expected_status
                if name == "ambiguous-product":
                    assert len(response["matching"]["matches"]) == 2
                summary["runs"][-1]["verified"] = True
            summary["status"] = "passed"
        finally:
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
            summary.setdefault("status", "failed")
            summary["server_stopped"] = process.poll() is not None
            (output / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
            print(output)


if __name__ == "__main__":
    main()
