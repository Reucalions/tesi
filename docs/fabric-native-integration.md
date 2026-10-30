# Collegamenti MCP a Fablo, ranking, Tiny-ME e provenienza

Questo incremento prepara il collegamento software ai contratti effettivi della
baseline. Il gateway `services/strategic_gateway/fabric_server.py` espone nove
tool MCP Streamable HTTP e chiama Fablo REST. Non importa librerie BWAF o
Tiny-ME nel processo degli agenti e non calcola risultati sostitutivi.

**Stato:** contratti, gateway, probe e adapter di provenienza implementati;
collaudi con Fablo HTTP simulato e SDK MCP effettivo. Chaincode PROV-O compilato
e verificato con lo stub Fabric. Non è stato effettuato un collaudo on-chain:
Docker non è raggiungibile e le porte Fablo locali 8800/8801 non rispondono nella verifica
del 18 ottobre 2026. Non è stato fornito un endpoint alternativo.

Il percorso Workforce con grafo non vuoto e validazione di una contromisura
**resta da collegare semanticamente**. Il nuovo servizio espone il formato
nativo e le analisi originali; non trasforma arbitrariamente il grafo MVP.

## Operazioni e verifiche

| Tool MCP | Operazione effettiva tramite Fablo | Verifica |
|---|---|---|
| `store_graph` | `ArgumentationContract:StoreGraph` | Rilettura `Get`, confronto del grafo e hash nella chiave |
| `get_graph` | `ArgumentationContract:Get` | Grafo nativo e hash della chiave |
| `rank_graph` | `ArgumentationContract:RankGraph` | Rilettura di classifica e grafo annotato |
| `get_rank_result` | `Get(key + "_rank")` | ID esatti delle strategie, unicità e score finiti |
| `get_annotated_graph` | `Get(key + "_annotated_graph")` | Struttura, riferimenti e pesi finiti |
| `analyze_ontology` | `AnalyzeOntology` | Abduzione, bonus e contrazione richiesti; risultato riletto |
| `get_reasoner_result` | `ReadReasonerResult` | Chiave e struttura originali del risultato Tiny-ME |
| `record_provenance` | Nuovo `StoreProvenance` | Record e bundle PROV-O riletti, digest e ID transazione |
| `read_provenance` | Nuovo `GetProvenance` | Identità del run, documento originale e relativi hash |

Le risposte usano `fabric-native-v1`, digest della richiesta, operazione,
canale e chaincode. HTTP 202, errori applicativi, risultati incompleti e
riletture discordanti non diventano successi. Non ci sono retry automatici
delle transazioni. Corpo degli errori HTTP, password e token non vengono
inoltrati agli agenti.

Le route predefinite sono `/invoke/{channel}/{chaincode}` e
`/query/{channel}/{chaincode}`, verificate nell'`index.ts` della baseline.
Il precedente bridge TypeScript usa di default un'altra famiglia di route
e trasporto MCP stdio; non è intercambiabile con questo contratto HTTP.
Le route REST restano configurabili per altri deployment.

## Grafo e interpretazione dei risultati

Il grafo nativo conserva `nodes(id,type)` e `edges(from,to)`. La chiave è
`graph:<SHA-256 del JSON canonico>`; un riuso con contenuto diverso è respinto.
Il chaincode originale continua a richiedere nodi e archi non vuoti.

La classifica conserva ordine, score e spiegazioni originali. Gli score non
vengono troncati a `[0,1]`, riordinati o normalizzati per adattarli a
`RankingResult` del MVP. I test includono intenzionalmente uno score sintetico
di `1.25` per verificare questa proprietà, non per attestare la scala BWAF.
Il contenuto del grafo annotato non è una prova della correttezza scientifica
del ragionamento o dell'equivalenza con i pesi del prototipo.

Il mapping da candidate/evidenze al vocabolario dell'ontologia deve definire
esplicitamente individui, relazioni, origine dei pesi e corrispondenza fra ID
nativi e ID delle candidate. Il grafo beneficio/impatto del MVP non viene
convertito perdendo segno o peso degli archi. Gli archi fra strategie non
vengono aggiunti per soddisfare soltanto il formato del chaincode.

## Tiny-ME

Il tool riceve contenuto OWL e nomi dei due individui da confrontare. La chiave
`analysis:<digest>` lega ontologia, risorsa e richiesta. Il gateway richiede
tutti e tre i servizi e confronta risposta e `ReadReasonerResult`.

La baseline `AnalyzeOntology` esegue una decodifica Base64 del transient;
la REST API applica già la decodifica del trasporto. Il gateway conserva
questi due livelli di codifica. Questo comportamento è verificato con fixture
di trasporto; resta da confermare sul deployment effettivo del professore.

`isCoherent=true` non viene tradotto in `accepted`: coerenza dell'ontologia e
applicabilità della contromisura sono proprietà differenti. Serve un mapping
di asset, azioni, prerequisiti e vincoli, con regole esplicite per interpretare
abduzione e contrazione. Il tool nativo non sostituisce ancora il tool di
dominio `validate_countermeasure` della Workforce. I risultati vuoti ammessi
quando l'ontologia è incoerente restano conservati come tali.

Il chaincode semantico della baseline usa `time.Now()` nel risultato: questo
incremento non ne dimostra il determinismo fra endorser e non modifica il
sorgente per mascherare la limitazione. Va verificato prima di attribuire
determinismo all'intero workflow on-chain.

## Provenienza su Fabric

`services/provenance_chaincode/` contiene un chaincode dedicato e separato dalle
baseline. Conserva documento JSON canonico (record e bundle PROV-O), digest
SHA-256 e ID della transazione di scrittura. La chiave del run è immutabile:
lo stesso documento è idempotente, uno differente viene rifiutato. La validazione
completa del modello PROV-O avviene nel gateway e nel client; il chaincode
controlla il run e il tipo di bundle e assicura persistenza e immutabilità.

Il documento canonico è conservato come stringa `document_json`: permette di
verificare gli stessi byte dopo la serializzazione Fabric, inclusi Unicode e
caratteri che Go può escapare nel JSON esterno.

L'adapter `FabricProvenanceTool` è collegato a `connect_backends`. Effettua
scrittura MCP, nuova lettura MCP e confronto con gli artefatti originali.
Conserva `provenance.jsonld`, `fabric_provenance_snapshot.json` e
`provenance_receipt.json`; `ArtifactSession.assert_complete()` li ricontrolla.
La ricevuta dichiara `storage_kind=fabric-world-state`,
`ledger_status=peer_readback_verified`, `block_commit_verified=false`.
Questa è una rilettura dal peer, non una verifica indipendente del blocco o
dello stato del commit. Il bundle contiene ancora `tesi:ledgerStatus=not_submitted`:
descrive il momento precedente all'invio, mentre la ricevuta separata descrive
il successivo esito. Alterare il bundle dopo l'invio cambierebbe il suo hash.

Il nuovo profilo `config/backends.otel-apache-fabric-provenance.json` mantiene
l'astensione sul grafo Apache vuoto e invia soltanto la provenienza al gateway
Fabric. Non abilita ranking non vuoti o Tiny-ME sulle candidate Apache.
Il profilo precedente continua a usare l'archivio su file.

## Avvio e probe

1. Rendere raggiungibile una rete Fabric/Fablo con i chaincode `argumentation`
   e `user-registry` della baseline. Installare inoltre `thesis-provenance`
   secondo il [README del chaincode](../services/provenance_chaincode/README.md).
   Non sono stati avviati o modificati i deployment esterni durante questo incremento.
2. Adattare `config/fablo.local.example.json` al deployment. Il file contiene
   soltanto il nome della variabile della credenziale, mai il suo valore.
   Impostare `THESIS_FABLO_SECRET` nell'ambiente del processo server.
3. Avviare il gateway dalla radice del repository:

```sh
.venv/bin/python -m services.strategic_gateway.fabric_server \
  --config config/fablo.local.example.json --port 8008
```

La discovery MCP verifica gli schemi; non certifica che Fabric sia disponibile.
Il probe esegue le operazioni effettive, salva ogni risultato e conserva anche
un riepilogo dei fallimenti in una directory nuova:

```sh
.venv/bin/python -m thesis_agents.mcp.fabric_probe \
  --graph /percorso/grafo-nativo.json \
  --ontology /percorso/ontologia.owl \
  --resource IndividuoRisorsa --request IndividuoRichiesta \
  --provenance /percorso/provenance.json \
  --output output/fabric-native-probe
```

Per il primo collaudo nativo si possono usare il grafo
`chaincode-argumentation/client/tests/graph_test_1.json` e l'ontologia
`chaincode/test_07.owl` della baseline ledger, con individui `IoTDevice001`
e `DDOS2025`, già usati dal suo test `TestAnalyzeOntology_Local_Success`.
Sono input di collaudo della baseline, non un nuovo caso CTI validato né una
prova di applicabilità delle contromisure dell'applicazione della tesi.
Il probe non esegue inferenze LLM, non produce una decisione della Workforce
e non genera automaticamente il mapping ontologico.

## Verifica e passi rimanenti

I test Python verificano gli schemi dei nove tool con l'SDK MCP, il ciclo
completo con HTTP Fablo simulato, errori e riletture discordanti, conservazione
degli score nativi e collegamento dell'adapter PROV-O alla Workforce CAMEL
con modello programmato. Non eseguono il motore BWAF o Tiny-ME.
I test Go usano `shimtest.MockStub` e le vere API Fabric: controllano schema
pubblico, scrittura, rilettura, ID transazione, idempotenza, conflitti e run
inconsistenti. È stata compilata anche la versione Linux amd64 del chaincode,
senza costruire o avviare un'immagine Docker.

Risultato complessivo: **400 test Python superati** in 63,87 secondi, con le
due deprecazioni RDFLib già presenti; **2 test Go superati**, `go vet`, Ruff,
formato e integrità delle modifiche verificati. Il riepilogo locale con hash
dei sorgenti e disponibilità degli endpoint è in
`output/fabric-integration-20261018/readiness.json`. Non è un run della Workforce
su Fabric e non contiene una ricevuta di commit.

Prima di dichiarare conclusa l'integrazione servono:

1. rete Fablo attiva, credenziali locali e chaincode PROV-O installato;
2. probe nativo effettivo, con verifica delle route e dei transient;
3. mapping documentato delle candidate/evidenze e validazione semantica di dominio;
4. esecuzione Workforce con grafo non vuoto, ranking reale e fallback semantico;
5. provenienza dell'intero run riletta dal ledger e confronto fra ripetizioni.

I repository esterni rimangono baseline in sola lettura; eventuali correzioni
ai loro contratti richiedono un incremento separato e tracciabile.
