# Fixture pytest condivise: inizializzano dati e stato isolati per ogni test.
# Pytest le inietta nei parametri con lo stesso nome, evitando setup duplicato.
from importlib.resources import files

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
