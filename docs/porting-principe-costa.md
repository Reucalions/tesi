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

## Passaggi ancora necessari

1. Allineare i binding Fabric nel backend condiviso: la sorgente usa
   `chaincode-argumentation` e `chaincode-semantic`, mentre la configurazione
   locale definisce `argumentation` e `user-registry`.
2. Allineare `ExplainAffinity`: il chaincode richiede chiave dell'ontologia e
   due IRI, ma il servizio importato passa solo i due IRI. Verificare anche
   la normalizzazione delle penalita e la distinzione tra errore tecnico ed
   esito semantico negativo.
3. Configurare endpoint, identita e certificati TLS sul backend, riusando la rete
   disponibile. Non e stata avviata o modificata alcuna rete.
4. Collegare il client MCP del framework al bridge stdio e adattare il grafo
   al contratto condiviso, senza implementare un ranking alternativo.
5. Verificare commit e rilettura: `get_provenance` costruisce la provenance dal
   record applicativo e non dimostra da solo la registrazione della raccomandazione
   sul ledger. La strategia deve restare raccomandata in dry-run.
6. Identificare il modulo LLM per annotazioni e argomenti citato dal professore,
   integrarlo come agente e collegare la dashboard esistente ai risultati.
