"""Verifica gli input distribuiti per la demo attraverso la CLI senza inferenza.

Le aspettative esatte su ID e ordine riguardano le candidate prefissate. Questi
test non misurano la generazione LLM e non sostituiscono le prove con Ollama.
"""

import json
from importlib.resources import files

import pytest

from thesis_agents.main import main
from thesis_agents.orchestration.artifacts import ARTIFACT_SCHEMAS


@pytest.mark.parametrize(
    "scenario,status,selected,attempts",
    [
        ("demo_01_nominal", "selected", "S_UPGRADE", [("S_UPGRADE", True)]),
        (
            "demo_02_no_maintenance",
            "selected",
            "S_ISOLATE",
            [("S_UPGRADE", False), ("S_ISOLATE", True)],
        ),
        (
            "demo_03_all_actions_prohibited",
            "no_valid_strategy",
            None,
            [("S_UPGRADE", False), ("S_ISOLATE", False), ("S_BLOCK", False), ("S_MONITOR", False)],
        ),
        ("demo_04_unsupported_lookup", "insufficient_evidence", None, []),
    ],
)
def test_demo_scenario_cli(tmp_path, scenario, status, selected, attempts):
    # Si leggono i JSON consegnati con il package, senza ricreare gli input nel test.
    input_source = files("thesis_agents").joinpath(f"data/{scenario}.json")
    input_path = tmp_path / "case.json"
    input_path.write_text(input_source.read_text(), encoding="utf-8")
    output = tmp_path / "run"
    assert main(["--mode", "fixtures", "--input", str(input_path), "--output", str(output)]) == 0

    artifacts = {
        name: schema.model_validate_json((output / f"{name}.json").read_text())
        for name, schema in ARTIFACT_SCHEMAS.items()
    }
    decision = artifacts["final_decision"]
    assert decision.status == status
    assert decision.selected_strategy_id == selected
    assert decision.explanation_method == "artifact-derived-v1"
    assert decision.agent_commentary.verification == "unverified"
    source_artifacts = set()
    for claim in decision.explanation_claims:
        for source in claim.sources:
            source_artifacts.add(source.artifact)
            value = json.loads((output / f"{source.artifact}.json").read_text())
            # Risolve il JSON Pointer contro i file reali, inclusi gli indici di lista.
            for token in source.pointer.split("/")[1:]:
                token = token.replace("~1", "/").replace("~0", "~")
                value = value[int(token)] if isinstance(value, list) else value[token]
            if source.artifact == "input":
                assert source.producer == "StaticTelemetry"
            else:
                activity = next(
                    a for a in artifacts["provenance"].activities if source.artifact in a.generated
                )
                assert source.producer == activity.agent
    assert source_artifacts == {
        "input",
        "runtime_evidence",
        "vulnerability_report",
        "candidate_strategies",
        "ranking",
        "semantic_validation",
    }
    validations = artifacts["semantic_validation"].validations
    assert [(v.strategy_id, v.valid) for v in validations] == attempts
    assert artifacts["provenance"].mode == "fixtures"
    assert json.loads((output / "input.json").read_text()) == json.loads(input_source.read_text())

    # Controlla il motivo del rifiuto, distinguendo capacità assenti da policy.
    if scenario == "demo_02_no_maintenance":
        assert validations[0].missing_requirements == ["maintenance_window"]
        assert validations[0].conflicts == []
        assert 'missing_requirements=["maintenance_window"]' in decision.explanation
    elif scenario == "demo_03_all_actions_prohibited":
        assert all(v.missing_requirements == [] for v in validations)
        assert all(len(v.conflicts) == 1 for v in validations)
        assert all(v.conflicts[0].startswith("Action prohibited by scenario:") for v in validations)
        assert "All published candidates were rejected" in decision.explanation
    elif scenario == "demo_04_unsupported_lookup":
        assert artifacts["vulnerability_report"].lookup_status == "unsupported"
        assert artifacts["vulnerability_report"].vulnerabilities == []
        assert artifacts["candidate_strategies"].strategies == []
        assert decision.ranking == []
