# Spiegazioni derivate dagli artefatti — 16 settembre 2026

Le prove precedenti avevano una decisione strutturata corretta, ma spiegazioni
LLM talvolta scorrette: `unsupported` veniva interpretato come mancato supporto
del vendor, assenza di vulnerabilità o invalidità di ogni contromisura.
Il mock attesta soltanto che il lookup non copre software/versione.

## Comportamento della pubblicazione

Lo Strategic continua a leggere i tre artefatti separati e a invocare i tool
CAMEL. Quando chiama `publish_final_decision`, il parametro `explanation`
viene conservato come `agent_commentary.text`, marcato `unverified`.
La spiegazione autorevole viene composta da campi strutturati della sessione:
osservazioni runtime, risultati del lookup, stime delle candidate, ranking,
capacità/policy e risultati della validazione.

| Campo in `final_decision.json` | Significato |
|---|---|
| `explanation` | Testo composto dai campi degli artefatti, con limiti espliciti |
| `explanation_method` | `artifact-derived-v1` nelle nuove pubblicazioni |
| `explanation_claims` | Affermazioni classificate e riferimenti alle fonti |
| `agent_commentary` | Testo originale del chiamante, non verificato semanticamente |

Ogni fonte indica l'artefatto, il produttore e un JSON Pointer. Ad esempio,
`vulnerability_report` con pointer `/lookup_status` rimanda al campo del report
pubblicato dal VulnerabilityAgent. I produttori delle fixture hanno il prefisso
`fixture:`. Ranking e validazione citano l'attività dello Strategic, e il testo
riporta separatamente il nome del backend che ha calcolato il risultato.

Le categorie sono `reported_fact`, `estimate`, `decision`, `limitation`.
Un dato riportato da un mock non diventa un fatto verificato nel mondo reale.
Le descrizioni e i rationale delle candidate, le osservazioni libere e le
spiegazioni narrative dei tool non vengono ricopiate nel testo autorevole.
Versioni consigliate o bollettini inventati in quei campi rimangono nei dati
originali, senza essere promossi ad affermazioni della spiegazione controllata.

Pydantic controlla il formato, mentre `assert_complete` ricostruisce i claim
dalle fonti correnti. Il controllo non si limita all'esistenza di citazioni.
I vecchi JSON sono ancora leggibili e classificati `legacy-unverified`, senza
modificare gli output storici. Nuove sessioni complete richiedono il nuovo metodo.

## Verifiche automatiche e fixture

Passano **83 test**, `ruff check .`, `ruff format --check .` e `git diff --check`.
Le regressioni verificano:

- testo inventato conservato come commento, senza contaminare la spiegazione;
- significato di lookup non supportato e distinzione fra stime e misure;
- risoluzione delle fonti contro i JSON dei quattro scenari e relativi produttori;
- rifiuto di claim, fonti o metadati alterati, anche con file e memoria coincidenti;
- pubblicazione idempotente, compatibilità storica e passaggio nei tool CAMEL reali
  con inferenza programmata per i test.

I quattro scenari senza LLM sono stati rieseguiti in
`output/explanation-fixtures-20260916T072837Z/`. Gli esiti restano rispettivamente
`S_UPGRADE`, `S_ISOLATE`, `no_valid_strategy`, `insufficient_evidence`.
Tutti producono gli otto artefatti e la copia dell'input.

Per riprodurre un caso, usare una directory di output nuova:

```bash
.venv/bin/python main.py --mode fixtures \
  --input thesis_agents/data/demo_04_unsupported_lookup.json \
  --output output/explanation-unsupported-new
```

## Prove con CAMEL e Ollama

Il batch `output/artifact-explanations-20260916T072747Z/` usa la CLI reale con
`--mode camel --workflow pipeline`, modello locale `tesi-qwen3:4b`, temperatura
0, massimo 2048 token per risposta, timeout del backend e limite esterno di
300 secondi per run. Conserva riproduttore, hash dei sorgenti, log, richieste
SDK e artefatti. I backend di dominio restano mock.

| Scenario | Esito | Secondi | Richieste LLM | Riferimenti risolti |
|---|---|---:|---:|---:|
| Nominale | `selected`, `S_UPGRADE` | 125,93 | 22 | 37 |
| Lookup non supportato | `insufficient_evidence`, selezione `null` | 107,90 | 30 | 15 |

Entrambe le prove hanno exit code 0 e otto artefatti validi, hash corrispondenti,
tre input distinti effettivamente ricevuti dallo Strategic e sequenza semantica
coerente con il backend. Non risultano tentativi di task falliti: questo non
esclude chiamate ridondanti o correzioni durante il ciclo del modello.
Il caso non supportato ha candidate, ranking e validazioni vuoti.
Queste sono due prove mirate, non una nuova matrice LLM completa ripetuta.

I controlli aggiuntivi in `explanation_audit.json` risolvono ogni JSON Pointer,
confrontano i produttori con le attività di provenienza, ricostruiscono i claim
dai file e verificano che la risposta del tool con la nuova decisione sia
effettivamente comparsa nei messaggi ricevuti dallo Strategic. Lo script
`explanation_audit_script.py` è conservato nel batch e non esegue inferenza.

Il commento libero dell'LLM nel caso non supportato usa ancora espressioni
come «no viable countermeasures» e «absence of valid candidates». Non è una
validazione dell'invalidità delle contromisure: nessuna candidata è stata
validata. Il testo è conservato in `agent_commentary` come `unverified`;
la spiegazione derivata indica invece esplicitamente copertura mancante e
assenza di una conclusione sulla validità di tutte le contromisure.
Il controllo migliora l'output autorevole senza attestare che il modello
abbia smesso di produrre interpretazioni imprecise.

## File interessati da questo intervento

- `thesis_agents/schemas/decision.py`: contratti della spiegazione e del commento.
- `thesis_agents/orchestration/explanations.py`: composizione e fonti.
- `thesis_agents/orchestration/artifacts.py`: pubblicazione, verifica e dipendenza
  diretta della decisione dall'input nella provenienza locale.
- `thesis_agents/agents/strategic.py`: istruzioni coerenti con il contratto.
- `tests/test_explanations.py`, `tests/test_demo_scenarios.py`,
  `tests/test_contracts.py`, `tests/test_camel_integration.py`: regressioni.
- `README.md`, `docs/architecture.md`, `docs/reading-guide.md`,
  `docs/structured-tools-runs.md` e questo documento: documentazione.

La semantica della Workforce e il DAG non cambiano in questo intervento.
Cambia la semantica del parametro `explanation` del tool finale: ora è commento
non verificato, mentre il campo di output omonimo è derivato dagli artefatti.
I backend mock, MCP, BWAF, Tiny-ME e la provenienza reale non sono modificati.
Resta necessario verificare separatamente la qualità delle strategie generate
e sostituire in futuro i mock con adapter dei backend finali.
