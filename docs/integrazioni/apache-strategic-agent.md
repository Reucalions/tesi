# StrategicAgent: conclusione del percorso Apache con evidenze insufficienti

Il profilo `config/backends.otel-apache-strategic.json` completa il percorso
strategico attualmente sostenuto dalle evidenze Apache. Lo Strategic legge
separatamente telemetria, report delle vulnerabilità e output del Countermeasure,
conserva le richieste pendenti e pubblica decisione e provenienza verificabile.

Questo incremento **non completa l'integrazione dei contratti BWAF, Tiny-ME
o Fabric**. Completa il ramo senza strategie confermate, con astensione
esplicita e un archivio MCP effettivo su file. Il nuovo servizio non è un
wrapper dei motori di ragionamento delle baseline.

## Comportamento e contratti

| Passaggio | Comportamento verificato |
|---|---|
| Ingressi | Tre artefatti distinti, con produttori e snapshot verificati |
| Grafo | Vuoto: le richieste di evidenza non diventano strategie |
| Ranking | Chiamata MCP a `empty-strategy-gate-v1`, che restituisce astensione esplicita |
| Validazione semantica | Nessuna invocazione: non ci sono candidate da verificare |
| Decisione | `insufficient_evidence`, senza selezione di contromisure |
| Provenienza | Scrittura MCP di record JSON e PROV-O JSON-LD, seguita da rilettura e confronto |
| Ledger | `not_submitted`: nessuna transazione Fabric |

L'adapter `empty-evidence-v1` richiede endpoint MCP dichiarati `real` per
ranking e provenienza. In questo profilo `real` identifica il servizio di
astensione e l'archivio su file effettivamente eseguiti, non l'esecuzione di
BWAF o Fabric. Un grafo non vuoto causa errore: nessun fallback alla formula
didattica del mock. Il backend semantico resta configurato `local-mock` per
compatibilità, ma non viene invocato. Il contratto semantico v1 non rappresenta
il nuovo report Ubuntu e resta escluso dalle chiamate remote.

Gli otto artefatti principali restano invariati. La spiegazione strutturata
distingue l'astensione dalla classificazione di strategie reali e riporta
le quattro richieste di verifica come lavoro aperto.

## Archivio MCP e PROV-O

Il servizio separato `services/strategic_gateway/server.py` espone:

- `rank_graph`: accetta soltanto grafi vuoti;
- `record_provenance`: salva il record e il suo export, con idempotenza per run;
- `read_provenance`: restituisce il contenuto salvato e i relativi digest.

Il client non legge i file del server: invia il record via MCP, verifica la
ricevuta e lo rilegge con il contratto `artifact-provenance-read-v1`.
Confronta contenuto, run, digest della richiesta, record e JSON-LD con gli
artefatti originali e con l'export deterministico. Solo dopo la rilettura
validata salva `provenance.jsonld` e `provenance_receipt.json` nella directory
del run. Anche il controllo finale della sessione verifica questi file.
Una ricevuta di scrittura senza rilettura coerente non completa il percorso.

L'export usa classi e relazioni della [raccomandazione W3C PROV-O](https://www.w3.org/TR/prov-o/):
`prov:Entity`, `prov:Activity`, `prov:SoftwareAgent`, `prov:used`,
`prov:generated`, `prov:wasGeneratedBy`, `prov:wasAssociatedWith`,
`prov:wasAttributedTo` e `prov:wasDerivedFrom`. IRI distinti per run evitano
collisioni tra analisi. Hash e nomi dei file usano proprietà applicative
nel namespace `urn:tesi:vocab:`. Il timestamp del run rimane un attributo del
run, senza inventare tempi di inizio e fine delle singole attività.

I test leggono l'export come RDF con RDFLib e verificano classi, hash e
relazioni; non si limitano a verificare la sintassi JSON. Questo controllo
non attesta la verità delle evidenze né esegue un reasoner OWL. L'hash della
provenienza stessa e la ricevuta restano fuori dal record inviato, evitando
autoriferimenti. La rilettura dell'archivio non è una prova di commit Fabric.

## Collaudo finale

Il run `output/apache-ubuntu-strategic/` usa gateway OTel, CTI Ubuntu e
servizio strategico MCP effettivi. CAMEL usa inferenza programmata, senza
LLM. Le chiamate di dominio validate sono:

1. `assess_ubuntu_package`;
2. `rank_graph`, sul grafo vuoto;
3. `record_provenance`;
4. `read_provenance`.

Le classificazioni delle 120 CVE coincidono con il precedente run
Countermeasure: 34 `fixed`, 28 `not_affected`, 46 `potentially_affected`,
12 `unknown`. Le quattro richieste pendenti su 58 CVE uniche sono conservate.
La decisione resta `insufficient_evidence`, con ranking e validazioni vuoti.

L'export RDF conserva **11 entità, 10 attività e 143 triple nel grafo del run**.
La verifica confronta l'archivio remoto con le copie rilette dal client,
controlla hash dei file, ricevuta e puntatori della spiegazione. Risultati:

- [riepilogo](../../output/apache-ubuntu-strategic/summary.json);
- [decisione](../../output/apache-ubuntu-strategic/artifacts/final_decision.json);
- [export PROV-O](../../output/apache-ubuntu-strategic/artifacts/provenance.jsonld);
- [ricevuta](../../output/apache-ubuntu-strategic/artifacts/provenance_receipt.json);
- [verifica](../../output/apache-ubuntu-strategic/verification.json).

Gli output sono locali e ignorati da Git. I warning sulla valutazione
gestionale CAMEL derivano dal modello programmato: il fallback a 80 non
costituisce una misura di qualità LLM.

Suite completa: **370 test superati**, inclusi 20 nuovi test su export RDF,
astensione, persistenza, alterazioni, contratti e passaggio CAMEL. Due warning
di deprecazione provengono dal parser JSON-LD RDFLib. Ruff, formato,
`git diff --check` e `pip check` superati. RDFLib è una dipendenza di sviluppo;
il servizio esporta JSON-LD senza dipendenze RDF aggiuntive a runtime.

## Riproduzione

Avviare OTel e servizio Ubuntu secondo la
[guida VulnerabilityAgent](ubuntu-vulnerability-agent.md#riproduzione).
Dalla radice di `tesi`, avviare il servizio strategico:

```sh
.venv/bin/python -m services.strategic_gateway.server \
  --data-dir output/strategic-provenance-store --port 8007
```

In un altro terminale, scegliendo una directory nuova:

```sh
.venv/bin/python tests/support/otel_workforce_smoke.py \
  --input config/input.otel-apache-recorded.json \
  --backends config/backends.otel-apache-strategic.json \
  --output-dir output/apache-ubuntu-strategic
```

La CLI applicativa può usare lo stesso profilo, con un modello esplicitamente
configurato. Questo incremento non contiene una nuova prova Ollama.
La successiva [prova Ollama completa](../esperimenti.md) è ora
documentata separatamente: primo fallimento e secondo run verificato dopo
la correzione delle fasi del Countermeasure, con due retry per timeout.

## Integrazioni ancora aperte

La baseline `semantic-cti-ledger-argumentation`, revisione
`a3dab4a5def79dda356dd753aa34306e03ea346a`, contiene il contratto
`chaincode-argumentation/argumentation-contract.go`. `StoreGraph` richiede
nodi e archi non vuoti; il formato `nodes(id,type)` / `edges(from,to)` non
codifica direttamente i pesi e i tipi supporto/attacco del prototipo.
`RankGraph` carica l'ontologia e invoca la libreria C++ via CGO. Una rinomina
dei campi perderebbe significato, quindi non viene applicata automaticamente.

Le API Tiny-ME analizzano ontologie e individui; servono un mapping di azioni,
capacità, policy e condizioni alle relative entità e un contratto pubblico
che rappresenti anche dati mancanti e contesto Ubuntu. Questi passaggi non
sono stati sostituiti da esiti semantici fittizi.

Nella verifica finale della sessione Docker non è raggiungibile e la porta
Fablo REST locale 8800 non risponde. Non è stato fornito un endpoint alternativo.
Restano quindi da preparare e collaudare separatamente mapping e servizi BWAF,
Tiny-ME e registrazione su ledger, oltre all'acquisizione delle evidenze
runtime e alla prova LLM. Il percorso senza strategie è concluso; la
validazione del percorso con contromisure confermate resta aperta.
