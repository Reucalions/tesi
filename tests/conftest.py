from importlib.resources import files

import pytest

from thesis_agents.orchestration.artifacts import ArtifactSession
from thesis_agents.schemas import StaticTelemetry


@pytest.fixture
def case():
    return StaticTelemetry.model_validate_json(
        files("thesis_agents").joinpath("data/log4j_case.json").read_text()
    )


@pytest.fixture
def session(case, tmp_path):
    return ArtifactSession(case, tmp_path / "run", mode="fixtures")
