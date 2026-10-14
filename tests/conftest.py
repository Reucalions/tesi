# Fixture pytest condivise: inizializzano dati e stato isolati per ogni test.
# Pytest le inietta nei parametri con lo stesso nome, evitando setup duplicato.
import socket
import subprocess
import sys
import time
from importlib.resources import files
from pathlib import Path

import httpx
import pytest

from thesis_agents.orchestration.artifacts import ArtifactSession
from thesis_agents.schemas import StaticTelemetry


@pytest.fixture
def case():
    # Rilegge la risorsa e costruisce un modello nuovo a ogni test. Un test può
    # rimuovere una capacità senza alterare l'input del test successivo o il JSON originale.
    return StaticTelemetry.model_validate_json(
        files("thesis_agents").joinpath("data/log4j_case.json").read_text()
    )


@pytest.fixture
def session(case, tmp_path):
    # tmp_path è una directory temporanea distinta fornita da pytest. Non viene
    # usata output/ e mode=fixtures impedisce di attribuire queste prove a un LLM.
    return ArtifactSession(case, tmp_path / "run", mode="fixtures")


@pytest.fixture
def http_server(tmp_path):
    processes = []

    def start(fault="none", *, kind="lookup", data_dir=None):
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            listener.listen()
            url = f"http://127.0.0.1:{listener.getsockname()[1]}/mcp"
            log = (tmp_path / f"server-{len(processes)}.log").open("w+")
            process = subprocess.Popen(
                [
                    sys.executable,
                    str(Path(__file__).parent / "support/mcp_http_server.py"),
                    "--fd",
                    str(listener.fileno()),
                    "--fault",
                    fault,
                    "--kind",
                    kind,
                    "--data-dir",
                    str(data_dir or tmp_path / f"store-{len(processes)}"),
                ],
                pass_fds=(listener.fileno(),),
                stdout=log,
                stderr=log,
            )
            processes.append((process, log))
        with httpx.Client(timeout=0.2, trust_env=False) as http:
            deadline = time.monotonic() + 10
            while time.monotonic() < deadline:
                if process.poll() is not None:
                    log.seek(0)
                    pytest.fail(log.read())
                try:
                    http.get(url)
                    return url
                except httpx.HTTPError:
                    time.sleep(0.02)
        pytest.fail("MCP test server failed to start")

    yield start
    for process, log in processes:
        process.terminate()
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
            process.wait(timeout=5)
        log.close()
