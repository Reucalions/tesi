# Matrice con il runner nel repository — 16 settembre 2026

Questa prova usa il nuovo runner `thesis_agents/demo.py` e l'audit in sola
lettura `thesis_agents/demo_audit.py`. I quattro agenti CAMEL, la Workforce,
il DAG, i contratti degli artefatti e i backend di dominio mantengono il
comportamento della revisione con spiegazioni derivate dagli artefatti.

## Comando e configurazione

```bash
.venv/bin/python -u -m thesis_agents.demo --mode camel --repetitions 2
```

Batch locale: `output/demo-matrix-20260916T074247Z-80665fa1/`.
Sono state completate otto nuove esecuzioni: quattro scenari per due ripetizioni,
in ordine sequenziale. Gli esiti delle prove storiche non sono stati riutilizzati
per riempire celle della matrice.

- Ollama locale, modello `tesi-qwen3:4b`, quantizzazione Q4_K_M.
- Endpoint `http://localhost:11434/v1`, temperatura 0, massimo 2048 token per risposta.
- Timeout del backend 300 secondi; limite esterno 300 secondi per run.
- Python 3.12.6, CAMEL 0.2.90, Pydantic 2.12.0, SDK OpenAI 2.54.0.
- Backend di dominio: lookup, ranking, validazione e provenienza tutti mock locali.

Il manifest conserva digest del modello, versioni, hash dei sorgenti e degli
input. Il riepilogo contiene esiti del processo e audit separati. Ogni cartella
di run conserva argomenti CLI, log, conversazioni SDK e artefatti.

## Esiti

**Otto run su otto completati e verificati**, con codice di uscita 0 della
matrice. Il 17 settembre sono stati riletti tutti gli artefatti e i log:
gli audit coincidono con quelli salvati dal runner, gli input con le copie
del manifest e i sorgenti con gli hash della prova. Non sono state avviate
nuove inferenze per questo ricontrollo.

| Scenario | Ripetizione | Decisione | Strategia | Secondi | Richieste LLM |
|---|---:|---|---|---:|---:|
| Nominale | 1 | `selected` | `S_UPGRADE` | 125,43 | 22 |
| Senza manutenzione | 1 | `selected` | `S_MONITOR` | 118,50 | 23 |
| Azioni vietate | 1 | `no_valid_strategy` | nessuna | 114,49 | 25 |
| Lookup non supportato | 1 | `insufficient_evidence` | nessuna | 150,78 | 37 |
| Nominale | 2 | `selected` | `S_UPGRADE` | 135,10 | 27 |
| Senza manutenzione | 2 | `selected` | `S_MONITOR` | 116,81 | 23 |
| Azioni vietate | 2 | `no_valid_strategy` | nessuna | 113,10 | 25 |
| Lookup non supportato | 2 | `insufficient_evidence` | nessuna | 111,14 | 30 |

La somma dei tempi dei processi è 985,35 secondi, circa 16 minuti e 25 secondi.
Le richieste LLM totali sono 212 e comprendono i modelli gestionali CAMEL.
Ogni run ha otto artefatti validi, copia dell'input, hash corrispondenti e
messaggi SDK che attestano la consegna dei tre input distinti e della decisione
allo Strategic. Fonti: [`summary.md`](../output/demo-matrix-20260916T074247Z-80665fa1/summary.md)
e [`summary.json`](../output/demo-matrix-20260916T074247Z-80665fa1/summary.json).

### Recuperi e variabilità osservati

Nel caso senza manutenzione l'upgrade è stato rifiutato per assenza di
`maintenance_window`, poi è stato accettato `S_MONITOR`: il fallback è
osservato nei tool in entrambe le ripetizioni, senza imporre al modello la
selezione delle fixture. Nel caso con azioni vietate sono state respinte tutte
e quattro le candidate in entrambe le prove, ma l'ordine è cambiato: nel secondo
run `S_BLOCK` precede `S_UPGRADE`, seguendo i punteggi di quel run.

Nel secondo nominale il primo tentativo dello Strategic si è fermato senza
decisione e provenienza. `ArtifactTaskHandler` ha respinto il falso successo;
CAMEL ha effettuato il secondo tentativo, che ha completato le pubblicazioni.

Nel primo caso non supportato i quality check CAMEL hanno richiesto retry per
Vulnerability, Countermeasure e Strategic, giudicando insufficienti i risultati
vuoti. Per questo scenario il lookup non coperto e i set vuoti sono invece
conformi ai contratti. L'SDK ha poi concluso i task con punteggi di qualità bassi.
Durante il retry dello Strategic una chiamata `validate_countermeasure` su
ranking vuoto è stata respinta dalla sessione; la pubblicazione finale è corretta.
Nel secondo caso non supportato il quality check ha richiesto retry per
Vulnerability e Countermeasure; non risultano errori di esecuzione dei tool.

| Run | Tentativi falliti per output mancanti | Retry richiesti dal quality check |
|---|---|---|
| Nominale, ripetizione 2 | Strategic 1/2, recuperato | nessuno |
| Lookup non supportato, ripetizione 1 | nessuno | Vulnerability, Countermeasure, Strategic |
| Lookup non supportato, ripetizione 2 | nessuno | Vulnerability, Countermeasure |
| Altri cinque run | nessuno | nessuno |

`failed_task_attempts` nel riepilogo conta soltanto il percorso SDK
`failed (attempt ...)` e non i retry del quality check. Gli eventi sopra
rimangono nel log e vengono riportati qui per evitare di interpretare un
elenco vuoto come assenza di tutti i retry. Il giudizio LLM di qualità del
task non sostituisce la validazione degli artefatti.
L'estrazione aggiuntiva degli eventi è conservata in
`observations-20260917.json` nel batch; gli artefatti di dominio non sono stati modificati.

## Controlli preliminari

Prima di avviare le inferenze sono passati **95 test**, `ruff check .`,
`ruff format --check .` e `git diff --check`. I dodici nuovi casi del runner
coprono anche timeout, output parziali, alterazioni dei file e consegna dei
messaggi SDK; i test non richiedono inferenza di rete.

Il runner ha inoltre eseguito i quattro scenari in modalità fixture:
`output/demo-matrix-20260916T074039Z-5fc62cf7/`. Quattro run su quattro risultano
verificati, con selezioni `S_UPGRADE`, `S_ISOLATE`, `no_valid_strategy` e
`insufficient_evidence`. Questo batch non contiene inferenza CAMEL/Ollama.
Il nuovo audit è stato anche confrontato con le due prove LLM precedenti
in `output/artifact-explanations-20260916T072747Z/`, entrambe riconosciute valide.

## Interpretazione e materiale per la presentazione

La verifica dimostra coerenza degli artefatti con i contratti e i mock, oltre
alla consegna degli input e della decisione nei messaggi dello Strategic.
Non certifica l'efficacia delle strategie, la verità di tutte le descrizioni
LLM o l'affidabilità generale su casi diversi da quelli provati.
Il commento LLM resta separato dalla spiegazione derivata, come descritto nel
[resoconto dedicato](artifact-explanations.md).

Due ripetizioni per scenario danno una prima osservazione della variabilità.
Temperatura 0 e configurazione uguale non implicano output identici.
Gli ID e l'ordine esatto delle strategie sono risultati della generazione;
il vincolo stabile è la selezione del primo candidato accettato secondo il
ranking e le policy. Il fallback viene annotato soltanto se realmente osservato.

La [guida del runner](demo-runner.md) descrive comandi, file e criteri di verifica.
Manifest, risultati e documentazione esistente sono le fonti della
[prima relazione complessiva](relazione-mockup.md) su teoria, architettura,
repository e attività svolte. Gli output restano locali ed esclusi da Git; questo resoconto conserva
nel repository i risultati essenziali e i riferimenti alle prove.
