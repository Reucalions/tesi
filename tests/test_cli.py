import json

from thesis_agents.main import main


def test_cli_fixtures_and_separate_runs(tmp_path):
    first = tmp_path / "first"
    assert main(["--mode", "fixtures", "--output", str(first)]) == 0
    decision = json.loads((first / "final_decision.json").read_text())
    assert decision["selected_strategy_id"] == "S_UPGRADE"
    before = (first / "provenance.json").read_bytes()
    assert main(["--mode", "fixtures", "--output", str(first)]) == 1
    assert (first / "provenance.json").read_bytes() == before


def test_schema_export_requires_no_credentials(tmp_path):
    assert main(["--export-schemas", str(tmp_path / "schemas")]) == 0
    assert len(list((tmp_path / "schemas").glob("*.schema.json"))) == 9


def test_missing_model_has_actionable_error(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("LLM_MODEL", raising=False)
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert main([]) == 1
    assert "LLM_MODEL" in capsys.readouterr().err
    assert not (tmp_path / "output").exists()
