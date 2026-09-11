# Test del comportamento visibile dalla CLI, eseguiti chiamando la stessa main.
# Non richiedono credenziali o rete: controllano codici di uscita, file e messaggi,
# oltre alle regole dei tool già coperte dalla suite di contratti.
import json

from thesis_agents.main import main


def test_cli_fixtures_and_separate_runs(tmp_path):
    # Il primo run deve riuscire; un secondo sullo stesso percorso deve fallire
    # lasciando intatta la provenienza. Si confrontano i byte, non solo il file esistente.
    first = tmp_path / "first"
    assert main(["--mode", "fixtures", "--output", str(first)]) == 0
    decision = json.loads((first / "final_decision.json").read_text())
    assert decision["selected_strategy_id"] == "S_UPGRADE"
    before = (first / "provenance.json").read_bytes()
    assert main(["--mode", "fixtures", "--output", str(first)]) == 1
    assert (first / "provenance.json").read_bytes() == before


def test_schema_export_requires_no_credentials(tmp_path):
    # L'esportazione è indipendente dall'LLM e produce input + otto schemi di output.
    assert main(["--export-schemas", str(tmp_path / "schemas")]) == 0
    assert len(list((tmp_path / "schemas").glob("*.schema.json"))) == 9


def test_missing_model_has_actionable_error(monkeypatch, tmp_path, capsys):
    # monkeypatch isola directory e variabili senza toccare la configurazione reale.
    # capsys cattura stdout/stderr: l'errore deve spiegare la variabile mancante e
    # non deve aver già creato una directory di run. Pytest ripristina tutto alla fine.
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("LLM_MODEL", raising=False)
    monkeypatch.delenv("LLM_API_KEY", raising=False)
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    assert main([]) == 1
    assert "LLM_MODEL" in capsys.readouterr().err
    assert not (tmp_path / "output").exists()
