# CLI del prototipo: interpreta le opzioni, valida l'input e sceglie l'esecuzione.
# Non implementa la collaborazione fra agenti: nella modalità camel questa viene
# delegata alla Workforce. La modalità fixtures serve invece a provare i contratti
# senza inferenza. Entrambe producono artefatti attraverso la stessa ArtifactSession.
import argparse
import json
import sys
from datetime import UTC, datetime
from importlib.resources import files
from pathlib import Path
from uuid import uuid4

from dotenv import load_dotenv

from thesis_agents.config import ModelSettings
from thesis_agents.orchestration.artifacts import ARTIFACT_SCHEMAS, ArtifactSession
from thesis_agents.schemas import StaticTelemetry


def main(argv: list[str] | None = None) -> int:
    # argv=None usa gli argomenti della shell; una lista esplicita permette ai test
    # di invocare la CLI senza avviare un processo. Il risultato è 0 o 1 per la shell.
    parser = argparse.ArgumentParser(description="Prototipo CAMEL per il caso Log4j")
    # mode decide se usare un LLM; workflow decide come CAMEL organizza i task.
    # --workflow ha effetto solo quando viene effettivamente avviata la Workforce.
    parser.add_argument("--mode", choices=("camel", "fixtures"), default="camel")
    parser.add_argument("--workflow", choices=("pipeline", "auto"), default="pipeline")
    parser.add_argument(
        "--input", type=Path, help="JSON StaticTelemetry; default: caso Log4j incluso"
    )
    parser.add_argument(
        "--output", type=Path, help="Cartella vuota; default: output/<timestamp>-<id>"
    )
    parser.add_argument(
        "--export-schemas", type=Path, help="Esporta JSON Schema senza eseguire agenti"
    )
    args = parser.parse_args(argv)
    try:
        # Gli schemi descrivono i contratti, quindi possono essere esportati anche
        # senza modello, credenziali o una sessione di analisi. Questo ramo termina qui.
        if args.export_schemas:
            args.export_schemas.mkdir(parents=True, exist_ok=True)
            schemas = {"input": StaticTelemetry, **ARTIFACT_SCHEMAS}
            for name, schema in schemas.items():
                path = args.export_schemas / f"{name}.schema.json"
                # «x» crea un file nuovo e fallisce se esiste già: evita sovrascritture.
                with path.open("x", encoding="utf-8") as stream:
                    json.dump(schema.model_json_schema(), stream, indent=2)
                    stream.write("\n")
            print(f"Schemi esportati: {args.export_schemas.resolve()}")
            return 0
        # Legge solo .env nella directory corrente, senza cercare nei genitori.
        # override=False preserva eventuali variabili già impostate nella shell.
        load_dotenv(Path.cwd() / ".env", override=False)
        # In modalità fixtures non si richiedono configurazione o credenziali LLM.
        settings = ModelSettings.from_env() if args.mode == "camel" else None
        # importlib.resources trova la fixture anche quando il package è installato,
        # senza dipendere dal percorso dello script. --input consente un caso diverso.
        content = (
            args.input.read_text()
            if args.input
            else (files("thesis_agents").joinpath("data/log4j_case.json").read_text())
        )
        # La validazione precede la creazione della sessione: un input malformato
        # non deve iniziare un run con dati parziali o campi non riconosciuti.
        case = StaticTelemetry.model_validate_json(content)
        # UTC rende il timestamp interpretabile su macchine in fusi orari diversi;
        # il suffisso casuale distingue anche due run avviati nello stesso secondo.
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        output = args.output or Path("output") / f"{stamp}-{uuid4().hex[:8]}"
        session = ArtifactSession(
            case, output, mode=args.mode, model=settings.model if settings else None
        )
        print(f"Modalità: {args.mode} | Output: {output.resolve()}", flush=True)
        # Gli import differiti caricano l'orchestrazione CAMEL solo quando serve.
        # Una stampa con flush rende subito visibile dove finiranno gli artefatti.
        if settings:
            from thesis_agents.orchestration.workforce import run_camel

            # Si passa una factory: la Workforce può costruire i backend dei vari
            # agenti senza conoscere come modello, endpoint e chiave sono configurati.
            decision = run_camel(session, settings.create_backend, workflow=args.workflow)
        else:
            from thesis_agents.fixtures import run_fixtures

            decision = run_fixtures(session)
        print(f"Esito: {decision.status}; strategia: {decision.selected_strategy_id or 'nessuna'}")
        print("Creati gli 8 artefatti JSON e la copia dell’input.")
        return 0
    except (ValueError, OSError, RuntimeError, ImportError) as exc:
        # Gli errori gestiti diventano un messaggio su stderr e un exit code 1.
        # La sessione può aver scritto artefatti parziali utili a capire il fallimento;
        # questo ramo non li cancella e non trasforma un fallimento in una decisione.
        print(f"Errore: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    # Supporta anche «python -m thesis_agents.main» con gli stessi codici di uscita.
    raise SystemExit(main())
