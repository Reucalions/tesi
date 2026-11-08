# Porting dei servizi condivisi su costa-thesis

Il 30 ottobre 2026 sono stati trasferiti selettivamente i componenti condivisi
da `principe-thesis` alle copie locali di `costa-thesis` nei due repository esterni.
Le modifiche sono nel working tree: nessun commit, push o cambio di branch.

| Repository | Revisione sorgente | Componenti trasferiti |
| --- | --- | --- |
| agent-based-cti-argumentation-pipeline | `441013262cf2247a7f6f4c6659b2761e7d53a8d6` | Bridge MCP, client REST, handler, esempio di configurazione e documentazione |
| semantic-cti-ledger-argumentation | `023b7118d1dcd3814a2dd9ebb0fe438a8158e315` | `fablo-rest`: contratti, backend SaaS, provenance, snapshot, inventario e test |

Il bridge espone 19 tool via stdio, compresi `rank_remediations`,
`validate_countermeasure`, `get_decision` e `get_provenance`.
Il framework MAS deve ancora collegarsi a questi contratti; il trasferimento
non abilita automaticamente un nuovo backend nel framework.

Non sono state importate le modifiche alla pipeline Python, i risultati sperimentali,
le credenziali o le configurazioni di rete. I file locali Identity/Ubuntu sono
stati preservati e verificati tramite hash. Dashboard Grafana e cinque casi
di argumentation erano gia presenti nel repository semantico su costa-thesis.

## Adattamenti necessari al porting

- Build del backend con `tsc`: nella sorgente mancava il file di configurazione
  richiamato dal comando Rollup.
- TypeScript 5.9.3, tipi Node 22/Jest 30 e Fabric Gateway 1.8.0 fissati;
  aggiunto `package-lock.json`. Richiesto Node.js almeno 22.12.0.
- UUID per grafi e decisioni: il solo timestamp poteva provocare sovrascritture
  tra richieste sulla stessa CVE, anche di tenant diversi. Rafforzato il test
  di isolamento congelando l'orologio.
- `.gitignore` del repository semantico aggiornato per tracciare i sorgenti SaaS,
  continuando a escludere dipendenze, build, dati e credenziali.

## Verifica

Nella copia isolata del porting sono passati compilazione TypeScript dei due
componenti, handshake MCP con discovery dei 19 tool e 66 test Jest in 13 suite.
I test del backend simulano Fabric: non costituiscono un collaudo del ledger reale.
La verifica SLSA usa l'ontologia gia presente nel repository semantico.
Gli hash dei sorgenti applicati coincidono con quelli della copia verificata.

Patch, backup dei file sostituiti, manifest con revisioni e hash, risultati Jest
e smoke test MCP si trovano in `output/porting-principe-costa-20261030/`.
Ogni componente importato contiene inoltre `PORTING-COSTA.md`.

Dopo il collaudo sono stati rimossi dalla copia isolata dipendenze npm, cache,
runtime Node temporaneo e sorgenti duplicati. Patch, backup, manifest e risultati
restano conservati. Per ripetere build e test usare i lock nei componenti importati.

## Consolidamento dei contratti del 31 ottobre

Applicati 23 file nei due componenti, con backup e verifica degli hash.
Binding chaincode configurabili, chiave ontologica aggiunta a ExplainAffinity,
mapping della risposta nativa Go, parsing stretto del ranking e gestione degli
errori tecnici sono ora implementati. Il bridge propaga snapshot/ontologia,
espone errorCode/isError, limita le richieste HTTP e usa le rotte legacy del REST.
Il SaaS dichiara ora la dipendenza runtime dotenv prima mancante.

L'assurance viene conservata con la decisione e riletta senza inventare una
verifica del codice; il digest dell'input precede l'arricchimento D3FEND.
Per record storici privi di assurance verificabile non viene dichiarato verified.

Verifica con Node 22.12.0: build dei due componenti, 105 test Jest in 14 suite,
12 test del bridge e smoke effettivo HTTP REST/MCP stdio. Quest'ultimo confronta
ranking e semantica, rilegge decisioni/provenance e verifica gli errori tecnici;
Fabric e identita restano simulati. Discovery: 19 tool.

Patch, backup, manifest e risultati: `output/backend-contracts-20261031/` nel
framework. I file `PORTING-COSTA.md` nei componenti descrivono contratti e scale.
Nessun commit/push, cambio di branch o modifica a Identity/Ubuntu, credenziali
e rete. La rete live non e collaudata: Docker non raggiungibile e porte locali
8800/7040/7041 chiuse durante la verifica.

## Passaggi ancora necessari

1. Verificare sulla rete esistente i binding configurabili argumentation/user-registry,
   i contratti distribuiti e le versioni: la configurazione non prova il deployment.
2. Verificare chiave ontologica, IRI e direzione resource/request sul caso di dominio.
   Il mapping usa score nativo /100 e penalita grezze, preservando condizioni e spiegazioni.
3. Configurare endpoint, identita e certificati TLS sul backend, riusando la rete
   disponibile. Non e stata avviata o modificata alcuna rete.
4. Collegare il client MCP del framework al bridge stdio e adattare il grafo
   al contratto condiviso, senza implementare un ranking alternativo.
5. Verificare commit e rilettura: `get_provenance` costruisce la provenance dal
   record applicativo e non dimostra da solo la registrazione della raccomandazione
   sul ledger. La strategia deve restare raccomandata in dry-run.
6. Identificare il modulo LLM per annotazioni e argomenti citato dal professore,
   integrarlo come agente e collegare la dashboard esistente ai risultati.


## Estensione autorizzata del 5 novembre 2026

Dopo l'ispezione completa e il permesso dell'utente, integrata la finalizzazione
nei due costa-thesis: 28 file sorgente/test/documentazione, con confronto degli
hash prima e dopo ogni applicazione e riferimenti Git invariati. Backend, bridge
e ArgumentationContract esistenti estesi; nessun servizio autonomo aggiuntivo.
Metodi StoreRecommendation/ReadRecommendation, persistenza delle validazioni,
ricevuta Gateway e readback, PROV-O collegata alla scelta effettiva e JSON-LD
corretto. Identita immutabile per CVE, idempotenza, conflitti e riavvio verificati.

640 test Python, 163 SaaS, 19 bridge e test Go/contract-api passati; build Node
22.12.0 e smoke HTTP/stdio con riavvio effettivo del backend. Fabric/Tiny-ME e
autenticazione simulati; nessun deployment live o esecuzione di remediation.
[Guida](integrazioni/strategic-finalization.md),
[evidenze](../output/shared-finalization-20261103/report.md).
