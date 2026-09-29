# Fonti, attribuzioni e scelte del mockup

Revisione bibliografica: 17 settembre 2026. Questo registro distingue le fonti
esterne dalle scelte implementative e dai risultati sperimentali del progetto.
Non ricostruisce retroattivamente un elenco completo delle consultazioni avvenute
durante lo sviluppo: dove non esiste una traccia, l'uso precedente non è attestato.
I riferimenti teorici verificati in questa revisione non sono automaticamente
le fonti da cui è stato scritto il codice.

## Origine della formula di ranking

La formula del mock **non è una formula BWAF tratta da un paper**. È una regola
dimostrativa già presente in `thesis_agents/tools/ranking_mock.py` nel commit
`17b7766ed43f6f0e599ef1679aa832ee6b4f9c2f`. Anche quella versione dichiara
che non implementa l'algoritmo dello smart contract BWAF. Non è documentata una
derivazione della formula dai due repository della proposta.

La ricostruzione seguente deriva direttamente dal codice:

1. `build_graph` assegna al nodo strategia il peso iniziale `0.5`.
2. Il nodo beneficio ha peso `security_benefit`; quello impatto ha peso
   `operational_impact`. Le stime sono in `[0,1]`.
3. Il beneficio supporta la strategia; l'impatto la attacca. Entrambi gli archi
   hanno peso `0.5`.
4. `rank_graph` somma il contributo degli archi entranti con segno positivo o
   negativo, usando i pesi originali dei nodi, senza iterazione.

```text
raw_score(s) = initial_weight(s)
             + sum(edge_weight * source_weight per supporto entrante)
             - sum(edge_weight * source_weight per attacco entrante)

score(s) = round(clamp(0.5 + 0.5 * beneficio(s) - 0.5 * impatto(s), 0, 1), 8)
```

Il valore iniziale e i due coefficienti sono **parametri dimostrativi scelti
nel prototipo**, non stimati su dati e non giustificati da un paper consultato.
L'uguaglianza dei coefficienti rende simmetrici i due contributi. Con esattamente
questi due archi e stime in `[0,1]`, il risultato è già in `[0,1]`: il clamp
è una protezione generale. Il beneficio crescente aumenta lo score, l'impatto
crescente lo riduce; questa proprietà algebrica non valida le stime o la bontà
operativa della strategia. A parità di score il codice ordina per ID.

Esempio della fixture: `0.5 + 0.5*0.95 - 0.5*0.20 = 0.875`.
Il risultato non è una probabilità di successo né un punteggio CVSS.
Per il grafo prodotto dal mock, prima dell'arrotondamento, ordinare per score
equivale a ordinare per `beneficio - impatto`.

Mossakowski e Neuhaus [BWAF-MN] distinguono aggregazione e influenza nelle
semantiche modulari; Potyka [BWAF-P] studia ulteriori proprietà e convergenza.
Sono riferimenti per inquadrare il dominio, **non citazioni a sostegno dei
coefficienti del mock** e non identificano la semantica del backend privato.
Non esiste una formula unica deducibile dal solo nome BWAF.

## Copie locali delle baseline private

Sono state consultate in sola lettura durante questa revisione:

| Baseline | Commit della copia locale | Esame effettuato |
|---|---|---|
| `agent-based-cti-argumentation-pipeline` [BASE-PIPELINE] | `c2ea54278bc5f44730693cdf7f86fc3584e54f70` | README, generatore del grafo e registrazione dei tool MCP |
| `semantic-cti-ledger-argumentation` [BASE-LEDGER] | `a3dab4a5def79dda356dd753aa34306e03ea346a` | README, contratto di ranking, wrapper Go/C++, header Graph e collegamento Tiny-ME |

Organizzazione dei remote Git: `sisinflab-swot`. L'attribuzione individuale
dei moduli e della libreria richiede conferma; l'organizzazione non viene
presentata come elenco completo degli autori. Il repository pipeline ha
modifiche locali a `mcp-fablo-server/package-lock.json` e file `.DS_Store`;
quello ledger risulta pulito. I file effettivamente esaminati hanno hash separati
in [baseline-locali.json](riferimenti/baseline-locali.json), così il commit
non viene confuso con una garanzia sull'intero albero locale.

### Che cosa è verificabile nel backend di ranking

Percorso osservato nel codice [BASE-LEDGER]:

```text
chaincode-argumentation/argumentation-contract.go : RankGraph
  -> graph.LoadOntology("onto/client_final_ontology.owl")
  -> graph.CreateGraph(...)
  -> graph/graph.go : ComputeRank
  -> graph/bridge.cpp : graph_compute_rank
  -> Graph::newCalculateRank_new()
```

Il contratto salva il grafo annotato e le strategie ordinate nel ledger.
Il formato d'ingresso ha nodi `id/type` e archi `from/to`; `StoreGraph` rifiuta
nodi o archi vuoti. Il risultato usa `suggestedStrategies` con nome, score e
spiegazione opzionale per percorsi a favore/contro e `strengthProduct`.

L'header `graph/lib/Graph.h` dichiara operazioni su nodi liberi/connessi,
percorsi ammissibili, pesi e ragionatore. La copia contiene `libgraph.so`, ma
nei due alberi consultati non è stato trovato il corpo C++ di
`Graph::newCalculateRank_new()`. I nomi delle funzioni e la struttura del
risultato **non bastano a ricostruire la formula**. Non è stata effettuata
una decompilazione o un'esecuzione della libreria.

Per documentare la semantica reale servono il sorgente che ha prodotto
`libgraph.so`, la sua versione e il riferimento scientifico indicato dagli
autori. Le stringhe `ISWA` e `CF` nei commenti dell'header non sono citazioni
bibliografiche sufficienti.

### Differenze già accertate rispetto al mock

Il generatore `app/src/semantic_assets/argumentation_graph.py` [BASE-PIPELINE]
usa CVE vulnerabili e relazioni OWL `hasSolutions`/`hasWorkarounds`, e aggiunge
archi diretti fra strategie distinte. Il mock invece proietta due stime per
candidata in supporto e attacco. Questi grafi non sono intercambiabili senza
una mappatura esplicita.

Il server `mcp-fablo-server/src/index.ts` registra i tool di memorizzazione,
ranking e lettura del grafo/risultato. Il wrapper semantico del ledger collega
Tiny-ME e COWL tramite CGO. Ciò documenta componenti presenti nei sorgenti
delle baseline; non dimostra che siano collegati o eseguiti dal repository `tesi`.

## Mappa delle attribuzioni

| Informazione nella relazione | Provenienza | Cosa appartiene al mockup |
|---|---|---|
| Quattro ruoli, convergenza nello Strategic, ranking seguito da validazione | Proposta di tesi [TESI], §§ 2, 4, 12 | Task CAMEL, DAG esplicito, prompt e controlli |
| Framework CAMEL e agenti comunicanti | [CAMEL], [CAMEL-SDK] | Configurazione Workforce, tool e adapter di verifica |
| Validazione e serializzazione Pydantic | [PYDANTIC] | Schemi del dominio, immutabilità e coerenza tra artefatti |
| Inferenza locale e parametri Ollama | [OLLAMA-API], [OLLAMA-MODELFILE], [QWEN] | Modelfile, limiti e protocollo sperimentale |
| CVE-2021-44228 | Bollettino Apache [LOG4J] | Input payment-api e lookup simulato |
| Supporti, attacchi e semantiche argomentative | [BWAF-MN], [BWAF-P]; backend [BASE-LEDGER] | Grafo beneficio/impatto e formula euristica |
| Ragionamento Tiny-ME | [TINYME]; wrapper [BASE-LEDGER] | Controlli simulati di capacità e policy |
| Entità, attività e agenti nella provenienza | [PROVO], [TESI] § 8 | JSON, hash e spiegazioni ricostruite dai campi |
| OpenTelemetry, MCP, OWL, OSV, SBOM, Fabric | [OTEL], [MCP], [OWL], [OSV], [SBOM], [FABRIC] | Punti di integrazione previsti, non implementazioni di quegli standard |
| Pipeline CTI e servizi ledger preesistenti | [BASE-PIPELINE], [BASE-LEDGER] | Contributo distinto dai repository di partenza |
| 95 test, 8/8 run, tempi, 212 richieste, recuperi | Test, manifest, summary e log locali | Risultati del progetto, non risultati dei paper |
| Font, colore e logo | [POLIBA], [PT-SANS], fonti degli asset | Impaginazione della relazione e delle slide |

## Materiale disponibile

- [Registro commentato delle fonti](riferimenti/README.md): citazioni e ambito d'uso.
- [Registro strutturato](riferimenti/fonti.json): identificativi, URL e data di consultazione.
- [Bibliografia BibTeX](riferimenti/bibliografia.bib): importabile nella tesi.
- [Proposta fornita dall'autore](riferimenti/proposta-agentic-cti.pdf): copia identificata con SHA-256.
- [Manifest delle baseline](riferimenti/baseline-locali.json): commit, stato e hash.

I link GitHub privati richiedono accesso. I loro sorgenti non sono stati copiati
in questo pacchetto. Le fonti pubbliche sono raggiungibili dai link; non sono
state archiviate integralmente. Per ciascun paper è dichiarata la parte
consultata, senza implicare una verifica integrale delle dimostrazioni.
