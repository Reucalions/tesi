# Prove dei quattro scenari con Ollama

Le correzioni e le verifiche successive del 15 settembre sono descritte nel
[resoconto dei tool strutturati](structured-tools-runs.md). Questo documento
conserva gli esiti e i limiti delle prove del 14 settembre.

Il 14 settembre 2026 sono state avviate due esecuzioni per ciascuno dei quattro
input dimostrativi, con CAMEL reale e inferenza locale. Il modello è
`tesi-qwen3:4b`, l'endpoint `http://localhost:11434/v1`, la temperatura HTTP 0,
il timeout per richiesta 300 secondi e il workflow `pipeline`. I task mantengono
il limite di due tentativi totali configurato nella Workforce.

Le prove sono sequenziali. Ogni avvio usa la CLI esistente con `--mode camel`,
`--workflow pipeline` e `--input thesis_agents/data/demo_*.json`. I log SDK sono
abilitati tramite `CAMEL_MODEL_LOG_ENABLED=true` e un `CAMEL_LOG_DIR` distinto.
Non sono state usate API a pagamento o contromisure eseguite sull'infrastruttura.

## Risultati e tracciabilità

Il batch iniziale è conservato nella workspace in
`output/demo-ollama-20260914T084356Z/`. Ogni directory `<scenario>-r<ripetizione>`
contiene:

- `artifacts/`: input e output pubblicati attraverso i tool;
- `llm/`: richieste, risposte e contesto dei tool registrati da CAMEL;
- `run.log`: log della CLI e dei worker;
- `run_summary.json`: durata, codice di uscita e controlli sugli artefatti.

`audit.json` raccoglie la verifica delle prove concluse. Gli output sono esclusi
da Git. I dati generati non vengono modificati o completati manualmente; un run
fallito conserva gli artefatti parziali.

Le durate misurano il processo CLI completo, inclusi inizializzazione ed eventuale
caricamento del modello. Le richieste LLM comprendono anche i ruoli gestionali.
I retry di task sono distinti dalle correzioni di una chiamata tool all'interno
dello stesso task. Temperatura 0 non ha prodotto candidate identiche fra i run.

| Scenario | Ripetizione | Esito iniziale | Secondi | Richieste LLM | Tentativi di task falliti |
|---|---:|---|---:|---:|---|
| Nominale | 1 | `selected`: `S_UPGRADE` | 138,78 | 26 | Strategic 1/2, recuperato |
| Nominale | 2 | `selected`: `S_UPGRADE` | 108,79 | 23 | Nessuno |
| Senza manutenzione | 1 | `selected`: `S_ISOLATE` | 108,01 | 24 | Nessuno |
| Senza manutenzione | 2 | `selected`: `S_BLOCK` | 126,05 | 25 | Nessuno |
| Azioni vietate | 1 | `no_valid_strategy` | 111,22 | 26 | Nessuno |
| Azioni vietate | 2 | Interrotto: nessuna decisione | 379,69 | 3 | Interruzione esterna |
| Lookup non supportato | 1 | Fallito: 5 artefatti su 8 | 89,29 | 39 | Strategic 1/2 e 2/2 |
| Lookup non supportato | 2 | Fallito: 5 artefatti su 8 | 90,59 | 39 | Strategic 1/2 e 2/2 |

Sono quindi completi cinque run degli otto iniziali. Nel caso interrotto è
presente soltanto `input.json`: una richiesta del TelemetryAgent è rimasta senza
risposta per oltre cinque minuti. È stato terminato soltanto il processo CLI di
quella prova, conservando log e risposta pendente. Le tre richieste conteggiate
includono quella senza risposta. Non è stata accertata la causa del rallentamento.

Nei due casi senza manutenzione l'upgrade è stato rifiutato per il medesimo
prerequisito assente. Nella seconda prova `S_BLOCK` e `S_ISOLATE` avevano entrambi
score 0,775: il tie-break per ID ha posto `S_BLOCK` prima di `S_ISOLATE`. La diversa
selezione è quindi coerente con il ranking generato in quel run.

## Controlli effettuati

Gli output presenti sono riletti con gli otto modelli Pydantic. Nei run completi
sono inoltre ricontrollati gli hash della provenienza e la sequenza di validazione
rispetto a ranking, candidate, capacità e policy, usando gli stessi mock.

Le risposte di `get_context` presenti nelle richieste LLM dello Strategic sono
confrontate con i tre file pubblicati e i produttori attesi: TelemetryAgent,
VulnerabilityAgent, CountermeasureAgent. Questa verifica legge i messaggi
effettivamente consegnati al modello, non soltanto lo stato finale della sessione.

## Limiti emersi nei contenuti

Le spiegazioni dei run nominali citano versioni target come `2.17.0 or later`
che il lookup mock non fornisce. Una spiegazione richiama anche conferme di
advisory del vendor che nessun tool ha consultato. Si tratta di affermazioni non
sostenute dalle fonti disponibili nel run, non di raccomandazioni verificate.

Alcune spiegazioni omettono di dichiarare che i backend sono mock o non riportano
esplicitamente i nomi dei produttori, sebbene i tre artefatti siano presenti nel
contesto e la provenienza registri i ruoli. I controlli strutturali proteggono
selezione e riferimenti; la qualità e l'attribuzione del testo libero restano
un requisito da migliorare prima della presentazione.

Il primo run con lookup non supportato ha pubblicato report e candidate vuoti,
ma si è fermato nello Strategic dopo tentativi di validare ID assenti dal ranking.
Il contratto ha respinto queste chiamate e il falso successo finale. Non è stato
prodotto un `FinalDecision`: questo è un fallimento di esecuzione, distinto
dall'esito di dominio atteso `insufficient_evidence`.

## Correzione del percorso con ranking vuoto

Dopo aver completato gli otto run iniziali è stata applicata una modifica
circoscritta, mantenendo gli stessi backend:

- il prompt dello Strategic distingue esplicitamente i percorsi con e senza candidate;
- il messaggio d'errore di `validate_countermeasure` su ranking vuoto indica di
  chiamare `publish_final_decision` con `selected_strategy_id` uguale a JSON `null`;
- la descrizione del tool finale chiarisce che quella pubblicazione crea anche
  `semantic_validation` vuoto, come già avveniva nel codice;
- il gestore dei task chiarisce che un tool può pubblicare più artefatti.

Non è stato introdotto un completamento procedurale al posto degli agenti.
La suite contiene un nuovo test di Workforce reale con inferenza programmata
che completa il lookup non supportato senza chiamare `validate_countermeasure`.
Sono passati 56 test e i controlli Ruff. Il test copre il protocollo, mentre le
nuove prove Ollama valutano il comportamento del modello dopo la correzione.

Il batch di verifica è conservato separatamente in
`output/demo-ollama-empty-path-20260914T090413Z/`: due prove del lookup non
supportato e una del caso con azioni vietate. Il processo CLI di ciascuna prova
ha un limite esterno di 300 secondi; questo limite appartiene all'esperimento,
non modifica la configurazione della Workforce.

| Scenario dopo la correzione | Esito | Secondi | Richieste LLM |
|---|---|---:|---:|
| Azioni vietate, nuova prova | Timeout esterno, solo input pubblicato | 300,03 | 3 |
| Lookup non supportato, prova 1 | `insufficient_evidence`, 8 artefatti validi | 90,89 | 26 |
| Lookup non supportato, prova 2 | `insufficient_evidence`, 8 artefatti validi | 104,32 | 33 |

Entrambe le nuove prove del lookup vuoto completano il percorso senza tentativi
di validare candidate inesistenti. I retry e le correzioni interne vanno letti
nei log; il superamento del test non certifica la qualità di ogni frase generata.

## Limite della generazione

Durante la nuova prova con azioni vietate, il log del server Ollama mostrava una
generazione ancora attiva dopo oltre 4.000 token nella risposta del TelemetryAgent.
La risposta non era terminata, quindi il log CAMEL non ne conteneva il testo finale.
Questo spiega l'attesa osservata, senza stabilire perché il modello non terminasse.

È stata aggiunta l'opzione `LLM_MAX_TOKENS`: un intero positivo, omesso dalle
richieste quando non configurato. Per la verifica locale si usa `2048`. Il valore
limita i token generati per risposta, non il contesto del modello; le risposte
troncate restano soggette agli stessi controlli e possono causare un task fallito.
Nel batch iniziale le risposte concluse registrate arrivavano al massimo a 756
token. Questa osservazione motiva il limite, ma non ne dimostra l'adeguatezza su
casi più complessi. La suite aggiornata comprende 62 test passati.

La prova mirata con il limite è conservata in
`output/demo-ollama-token-cap-20260914T091240Z/`.

Esito verificato il 15 settembre: la prova del 14 settembre è terminata con
codice 1 dopo 222,66 secondi e 35 richieste LLM registrate. È presente soltanto
`input.json`, senza alcuno degli otto artefatti di output. Il limite non ha quindi
risolto il problema di pubblicazione.

Al primo tentativo, il TelemetryAgent ha inviato a `publish_runtime_evidence`
un payload incompleto e un altro con escape non validi; Pydantic ha respinto
entrambi. Al secondo tentativo Ollama ha restituito un errore HTTP 500 per
argomenti di tool non validi (`unexpected end of JSON input`). Il log non
consente di attribuire con certezza quest'ultimo errore al limite di token.

Dopo il fallimento di Telemetry, la pipeline CAMEL ha comunque avviato gli
altri task, che sono falliti per i prerequisiti mancanti. I contratti hanno
impedito la pubblicazione di risultati incoerenti, ma non hanno evitato le
chiamate LLM inutili a valle. Le prossime verifiche devono concentrarsi sulla
serializzazione del payload al confine agente-tool e sull'arresto dei task
dipendenti quando il produttore fallisce, prima di ripetere l'intera matrice.
