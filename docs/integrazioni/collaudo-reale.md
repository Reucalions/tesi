# Primo collaudo reale: Fabric, MCP e casi controllati

## C4-r3 completato in un'unica esecuzione: 12 novembre 2026

Il nuovo launcher real/camel/pipeline ha concluso tutti gli otto nodi del DAG
con exit code 0, finalizzazione `completed` e rilettura del ledger. Timeout
LLM 600 s; durata 1224,254 s. Nessuna ripresa da altri run: i recuperi automatici
interni CAMEL restano visibili nel log e il DAG e quello originale completato.

Commit distinto nel blocco 28, validation_code=0; record/provenance/ricevuta
identici nelle verifiche successive MCP, grafo coerente con il canonico e rinnovo
credenziali passato. Metadati SaaS originali salvati, archivi e vecchi commit invariati.
Esito `requires_prerequisites`: nessuna selezione o esecuzione di contromisure.
Manutenzione mancante e prerequisito testuale non riconciliato restano nel risultato.
[Report e audit C4-r3](../../output/c4-collaudo-20261112-r2/report.md).
Le sezioni sotto conservano la storia dei tentativi e della ripresa C4-r2.

## C4: ripresa verificata il 12 novembre 2026

Il launcher C4-r2 ha completato sette nodi e il commit, poi e fallito nell'ultimo
nodo per timeout Ollama. La ripresa CAMEL dell'ultima fase e terminata con exit
code 0 e `shared_finalization=completed`, con timeout LLM 600 s. Il record e
quello originale nel blocco 25: nessuna nuova decisione o sostituzione del commit.

Passati rilettura MCP indipendente, confronto integrale di record/provenance/
ricevuta, controllo del grafo e rinnovo credenziali dopo un rifiuto controllato.
Salvati tre metadati SaaS reali e verificata l'integrita degli archivi precedenti.
Esito `requires_prerequisites`, manutenzione mancante, nessuna strategia selezionata.

Non e un launcher integrale riuscito: il DAG originale resta failed; la copertura
degli otto nodi tra launcher e ripresa e dichiarata separatamente nel
[report corrente](../../output/c4-collaudo-20261112-r1/report.md).
Le sezioni datate sotto conservano gli esiti precedenti.

## Chiusura C1 verificata: 7 novembre 2026

C1-r2 ha completato il launcher reale CAMEL/Ollama e tutti gli otto nodi del DAG
con `dry_run_completed` e finalizzazione condivisa `completed`.
Esito decisionale: **requires_prerequisites**, con `selected_strategy_id=null`.
Tiny-ME restituisce abduzione 38 e score 62; il controllo operativo restituisce
`requires_review`. Il completamento tecnico non attesta una contromisura accettata.
C2/C3 restano completati; C4 e i suoi tentativi di ripresa restano non completati.

[Report corrente](../../output/case-improvements-20261106/report-C1.md). Le sezioni datate sotto conservano la preparazione
e gli esiti precedenti; Logback e ora adottato nel protocollo v2.

C1 conserva una copia dei nuovi metadati SaaS e un manifest SHA nel task.
Alcuni test preesistenti puliscono gli store predefiniti: eseguire ulteriori suite
in una copia isolata, mantenendo separati directory di test e dati del servizio.
La rete e il ledger non sono stati azzerati. Runtime/ontologia effettivi e rollback
sono nel manifest del task; snapshot SaaS in RAM da riregistrare dopo il riavvio.

Avviato il 5 novembre e concluso il 6 novembre 2026. La rete usa il repository
`/Users/reucalion/Desktop/semantic-cti-ledger-argumentation` su `costa-thesis`.
Non e stata avviata da una copia isolata del repository. Il framework rimane `full`.

## Avvio effettivamente verificato

Seguiti README principale e guida `chaincode-argumentation/readme.md` del repository:

1. Build di `user-registry-custom:1.0` e `argumentation-chaincode:1.0` dalle
   directory originali su costa-thesis. Piattaforma `linux/amd64` per le librerie
   native distribuite. Build CGO effettiva, non il precedente harness senza CGO.
2. Fablo 2.4.1, versione indicata dalla guida di argumentation e dallo schema della
   configurazione; `./fablo up fablo-config.json` dalla root originale.
3. Backend `fablo-rest/dist/index.js` compilato e avviato con PM2, Node 22.12.0,
   porta 8800, discovery TLS sul peer locale e certificato generato da Fablo.
4. Bridge MCP stdio del secondo costa-thesis compilato e collegato al backend.

Sul Mac l'hook del repository richiede GNU sed: la prima esecuzione con BSD sed
e fallita. GNU sed 4.9 e stato compilato e installato solo in
`output/real-cases-20261105-r1/runtime-gnu-sed`; l'hook originale e stato rieseguito
con quel PATH. `fablo-config.json`, README, `.env` e compose originale sono invariati.
Nessun prune, reset o cancellazione di reti/ledger.

La build nativa ha richiesto due correzioni minime nei sorgenti costa-thesis:
import `strconv` ancora necessario e conversione esplicita `C.bool` nel callback
IRI. Il primo run delle fonti ha richiesto la correzione del nome del parametro
di pinning del dataset nel launcher Python. Patch, backup e fallimenti conservati.

## Risultato MCP e ledger

Confermati canale `my-channel` e definizioni committed versione 1.0, sequenza 1,
di `argumentation` e `user-registry`. Il bridge espone 21 tool.

Sono passati, con autenticazione e Fabric reali, `get_active_snapshot`,
`store_graph`, `get_graph`, `rank_graph`, `get_rank_result` e `get_annotated_graph`.
Usato il primo grafo di benchmark esistente con una nuova chiave: roundtrip JSON,
nomi dei candidati, score finiti, clash diretto negativo e prodotti dei cammini
controllati sugli output effettivi. Non e ancora una finalizzazione MAS reale.

Il core ha restituito anche un cammino `against` con prodotto positivo, coerente
aritmeticamente con i suoi archi. Questa osservazione non concorda con la semplice
interpretazione di `against` come cammino a prodotto negativo introdotta nei
controlli offline: il significato del formato va chiarito. Non si modifica il
binario per farlo aderire a un'aspettativa e non se ne attesta equivalenza al paper.

I tool MCP gestiscono grafi, ranking, validazioni, snapshot, asset e finalizzazioni.
L'avvio/arresto dei container rimane gestito da Fablo; non e esposto dal bridge.

## Fonti e quattro tentativi

Due copie isolate dell'applicazione Java esistente hanno prodotto build reali,
SBOM e log SDK coerenti per 2.14.1 e 2.26.1, senza cambiare il POM originale.
C4 riusa la fonte vulnerabile e cambia soltanto `maintenance_window` nella policy.
C3 modifica il solo nome prodotto su una copia dell'export, da Apache Log4j Core
a log4j-core, dichiarandola degradazione sintetica controllata. Le osservazioni
originali e i loro hash sono conservati.

Le esecuzioni diagnostiche riusano `run_camel_sources`, `connect_real_sources`,
gli handler HTTP, CTI MCP, OSV live e il modello locale gia installato
`tesi-apache-qwen3:4b-32k`. Nessun modello programmato o backend mock di ripiego.
Il loro perimetro e la Workforce dei tre produttori: non sono quattro esecuzioni
complete del launcher `--backend-mode real` fino alla raccomandazione.

La sorgente CTI reale conferma tre finding per il caso vulnerabile. Il builder
Bottalico non trova individui Solutions/Workarounds collegati a queste tre CVE
nel KG originale di 5 GB. Questo e un ostacolo dati al checkpoint canonico,
distinto da eventuali errori del modello nella pubblicazione delle candidate.
Non vengono creati rimedi ontologici o binding nuovi per aggirarlo.

Esiti, tempi e artefatti dei singoli tentativi sono nel
[report conclusivo](../../output/real-cases-20261105-r1/report.md). Nei casi senza
candidate, l'assessment puo completarsi con fasi native non applicabili; un errore
di pubblicazione o un timeout resta un fallimento tecnico, non un'astensione valida.

## Gestione della rete gia inizializzata

La rete e il backend sono lasciati attivi per il lavoro successivo. Per riavviare
la rete gia generata, dalla root del repository costa-thesis:

```sh
DOCKER_DEFAULT_PLATFORM=linux/amd64 ./fablo start
```

Per arrestarla usare il comando esistente `./fablo stop`. Non ripetere prune/reset
per risolvere un errore di applicazione. PM2 usa un home locale al collaudo:

```sh
TESI_REAL_RUN=/Users/reucalion/tesi/output/real-cases-20261105-r1
TESI_NODE22=/Users/reucalion/tesi/output/shared-finalization-20261103/runtime/node_modules/node/bin/node
PM2_HOME="$TESI_REAL_RUN/pm2-home" "$TESI_NODE22" \
  "$TESI_REAL_RUN/process-manager/node_modules/pm2/bin/pm2" list
```

Gli stessi argomenti PM2 permettono `logs fablo-rest`, `stop fablo-rest` e
`restart fablo-rest`. Le credenziali non sono nei profili salvati: il bridge legge
quelle gia presenti nel suo `.env`. Conservare `fablo-target`, i dati backend e
le directory dei runtime/PM2; non cancellarli come output rigenerabili mentre il
servizio li usa. Nessun commit/push o esecuzione di contromisure effettuati.
