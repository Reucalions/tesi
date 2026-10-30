# Resoconto del progetto e punto di ripresa

Questo documento conserva il contesto operativo della conversazione: attività,
decisioni tecniche, motivazioni verificabili, risultati e lavoro ancora aperto.
Serve per riprendere in una nuova chat senza rileggere l'intera conversazione.
I documenti e gli artefatti collegati contengono i dettagli; questo file non
sostituisce i risultati dei test né la relazione destinata al professore.

**Revisione documentale del 29 ottobre 2026:** aggiornate la
[mappa dell'architettura](docs/architettura-implementata.md), la guida al codice,
README, contratti e stato MCP; aggiunto
[stato-progetto.md](docs/stato-progetto.md) come percorso di studio. La vecchia
mappa del solo profilo mock è conservata in
`docs/architettura-profilo-mock.md`. Nuove figure PNG/SVG/PDF in `docs/materiali/`:
`architettura-aggiornata` e `confronto-mockup-attuale`. Sono schemi dei componenti,
non BWAF esportati dal run Apache, che rimane vuoto.
La copia `relazione-aggiornata-20261029.docx` conserva la relazione manuale e
aggiunge nota di lettura e capitoli 19–24. `relazione.docx` non è stato riscritto:
259 elementi originali del corpo e due immagini sono preservati nella nuova
copia. I capitoli nuovi sono anche in Markdown e nel PDF separato
`aggiornamento-relazione-20261029`; il vecchio PDF e le slide restano storici.
Il generatore additivo è `docs/materiali/genera_aggiornamento.py`, distinto dal
generatore storico che sovrascriverebbe le revisioni manuali.
Hash e controllo di conservazione: `docs/materiali/aggiornamento-verifica-20261029.json`.
Le ultime prove citate restano quelle del 18 ottobre; non sono stati avviati
servizi, nuove inferenze o verifiche on-chain. Per l'impaginazione è stato
usato un ambiente temporaneo separato `/private/tmp/tesi-docs-20261029`.

**Task in corso dopo la prova Ollama:** l'utente ha scelto di completare prima
i collegamenti MCP a grafo/ranking/Tiny-ME/PROV-O/Fablo, rinviando il nuovo
caso con telemetria e inventario coerenti. È stato implementato il
[gateway nativo Fabric](docs/fabric-native-integration.md): nove tool HTTP,
contratti separati dal MVP, probe senza LLM e chaincode PROV-O dedicato con
adapter Workforce e rilettura verificata. I test usano HTTP Fablo simulato,
MCP effettivo e stub Fabric; il chaincode compila anche per Linux amd64.
**Non dichiarare conclusa l'integrazione on-chain o il percorso con candidate.**
Docker non è raggiungibile nemmeno fuori sandbox, Fablo localhost:8800 non
risponde; manca un endpoint alternativo. È stata posta una domanda asincrona
all'utente sulla rete da utilizzare. Non sono stati avviati Docker o reti,
né modificati i repository esterni. Restano installazione del chaincode,
probe on-chain, mapping al vocabolario nativo e validazione di dominio delle
candidate. Coerenza Tiny-ME non equivale ad applicabilità della mitigazione;
il grafo MVP non viene convertito scartando pesi o segni. Il nuovo profilo
`config/backends.otel-apache-fabric-provenance.json` collega solo la
provenienza Fabric e mantiene l'astensione per Apache senza candidate.
Go 1.25.4 è stato scaricato da fonte ufficiale con hash verificato soltanto
in `/private/tmp/tesi-go-toolchain`; dipendenze e cache sono temporanee.
Nessuna installazione di sistema, inferenza a pagamento, commit o push.
Verifica dell'incremento: **400 test Python superati**, 2 warning RDFLib già
presenti; **2 test Go**, `go vet` e compilazione Linux amd64 superati. Ruff,
formato e integrità verificati. Readiness e hash:
`output/fabric-integration-20261018/readiness.json`; conferma che Docker e le
porte Fablo 8800/8801 non sono raggiungibili. Nessuna ricevuta on-chain generata.

**Punto di ripresa aggiornato:** conclusa la **prova completa con inferenza
Ollama effettiva** sui quattro agenti del caso Apache registrato.
`output/apache-ollama-20261018-r2/` completa tutti gli artefatti e supera
l'audit offline: 120 CVE (34/28/46/12), quattro richieste pendenti su 58 CVE
uniche, decisione `insufficient_evidence`, nessuna contromisura selezionata.
Il confronto conserva tutte le classificazioni del collaudo programmato;
provenienza MCP, rilettura e RDF sono verificati.
La prima prova r1 è fallita nel Countermeasure: due chiamate di pubblicazione
scritte come testo. È stata aggiunta una policy per le fasi Countermeasure,
senza pubblicazioni automatiche. R2 riesce ma richiede un retry Countermeasure
e uno Strategic per timeout: **1.284,92 s, 28 richieste registrate, 26 risposte**.
Modello locale `tesi-apache-qwen3:4b-32k`, contesto 32768, risposta 8192,
temperatura 0. I sorgenti originali di entrambi i run sono conservati con hash.
**Non è ancora dimostrata affidabilità senza recuperi**: rimangono latenza,
timeout e proposte testuali non eseguite. Le evidenze sono storiche,
non una nuova acquisizione runtime. BWAF/Tiny-ME/Fabric restano aperti;
la ricevuta è `artifact-files`, `ledger_status=not_submitted`.
Dettagli: [prova Apache/Ollama](docs/apache-ollama-use-case.md).
Ultimi controlli: **376 test superati**, Ruff e integrità; due deprecazioni
del parser RDFLib. I 69 test backend restano un risultato precedente.

## 1. Repository, branch e vincoli concordati

| Repository | Percorso locale | Ruolo |
|---|---|---|
| `tesi` | `/Users/reucalion/tesi` | Prototipo multi-agente, client, contratti, gateway e documentazione |
| `agent-based-cti-argumentation-pipeline` | `/Users/reucalion/Desktop/agent-based-cti-argumentation-pipeline` | Baseline CTI, dataset cve2owl, export OTel e servizio CTI aggiunto |
| `semantic-cti-ledger-argumentation` | `/Users/reucalion/Desktop/semantic-cti-ledger-argumentation` | Baseline per integrazioni successive dei servizi strategici |

- Il branch attivo di `tesi` è **`full`**. `mockup` è indicato nella
  documentazione come baseline dimostrativa da preservare.
- Il branch del primo repository esterno è **`costa-thesis`**; il commit di
  riferimento per l'ultima verifica è
  `3b483624286262f2e0ac94b4b950b904a5dc2ad4`.
- Nei repository esterni si aggiungono componenti separati. Non si riscrivono
  gli algoritmi preesistenti per adattarli al risultato desiderato.
- L'integrazione avviene un componente alla volta: contratto, test isolati,
  chiamata effettiva al servizio, poi collegamento al prototipo.
- I backend sono servizi black box: il processo degli agenti non importa il
  codice del motore CTI né apre il suo database. Il server esterno può usare
  internamente gli algoritmi della propria baseline.
- Smart contract e ledger dovranno essere invocati tramite tool esterni.
  Il ledger ha soprattutto funzione di registrazione, audit e tracciabilità;
  non sostituisce il ragionamento degli agenti.
- L'utente preferisce Ollama locale e non vuole sostenere costi per inferenze
  cloud. Non usare la presenza di una chiave in `.env` come autorizzazione a
  eseguire chiamate a pagamento. Non riportare segreti nella documentazione.
- Non sono stati effettuati commit o push per l'ultimo incremento.

## 2. Architettura mantenuta

Sono mantenuti quattro agenti CAMEL: `TelemetryAgent`, `VulnerabilityAgent`,
`CountermeasureAgent`, `StrategicAgent`. La modalità pipeline rimane il
percorso di riferimento, ma le dipendenze dati formano un DAG:

```text
Telemetria → TelemetryAgent → RuntimeEvidence ───────────────┐
                                  │                        │
                                  ├→ VulnerabilityAgent    │
                                  │        ↓               │
                                  │  VulnerabilityReport ──┤
                                  │        │               │
                                  └────────┴→ CountermeasureAgent
                                                  ↓        │
                                         CandidateStrategies
                                                  │        │
                                                  └────────┤
                                                           ↓
                                                    StrategicAgent
                                                           ↓
                                              Tool strategici e decisione
```

Lo Strategic legge separatamente i tre artefatti tramite `get_context`.
`RuntimeEvidence` resta autorevole e disponibile: il report delle vulnerabilità
non lo ingloba e non lo sostituisce. Il Countermeasure usa il contesto runtime
e il report, oltre all'eventuale ingresso SBOM/OSV.

Pydantic definisce i contratti; `ArtifactSession` conserva e controlla lo stato
condiviso, le pubblicazioni, le dipendenze e la completezza. CAMEL gestisce gli
agenti e le chiamate ai tool. L'LLM non è la fonte autorevole dei dati remoti.
I test con `ScriptedToolModel` attraversano CAMEL, ma **non sono inferenze LLM**.

MCP è un protocollo di accesso ai tool, non un agente. È stato impiegato sia
per il lookup CTI del Vulnerability sia per i tool dello Strategic. Gli ingressi
telemetrici e SBOM/OSV usano gateway HTTP separati: non tutte le comunicazioni
devono diventare MCP. La scelta dei backend avviene tramite configurazione;
un server MCP mock verifica il trasporto ma non rende reale il suo algoritmo.

Riferimenti: [architettura](docs/architecture.md),
[piano MCP](docs/mcp-integration-plan.md),
[artefatti](docs/artifact-explanations.md).

## 3. Percorso svolto prima dell'ultimo incremento

La conversazione ha accompagnato questi passaggi, documentati nel repository:

1. Prototipo con quattro ruoli, mock di dominio, artefatti Pydantic e controlli
   sulle pubblicazioni; chiarimento della distinzione fra esecuzione programmata
   e agenti effettivamente guidati da LLM.
2. Inferenze locali con Ollama, scenari dimostrativi, runner e matrice di prove.
   Sono conservati anche fallimenti e limiti, senza presentarli come successi.
3. Preparazione della relazione, del PowerPoint modificabile per una
   presentazione di 15 minuti e della demo. Fonti, baseline private e scelte
   originali sono distinte nella documentazione bibliografica.
4. Client MCP, server mock e selezione dei backend; successivo servizio CTI
   esterno per il dataset cve2owl e adapter del VulnerabilityAgent.
5. Gateway OpenTelemetry e gateway SBOM/OSV; applicazione Java locale con log
   SDK e SBOM Maven coerenti con la stessa build; collaudi programmati e Ollama.
6. Correzioni dei problemi di pubblicazione: payload distinti per fonte,
   strumenti disponibili per fase, budget del contesto e gestione della memoria
   nei cloni CAMEL. L'ultimo collaudo documentato di quel percorso conclude
   quattro inferenze su quattro senza retry, ma le due prove positive scelgono
   strategie diverse: il flusso funziona, la raccomandazione non è deterministica.
7. Ricerca di un caso Apache già presente nella baseline, recupero delle fonti
   originali e integrazione dei log registrati descritta sotto.

Documenti per approfondire senza ricostruire la chat:

| Argomento | Documento |
|---|---|
| Demo e matrice iniziale | [demo-matrix-runs.md](docs/demo-matrix-runs.md) |
| Tool strutturati | [structured-tools-runs.md](docs/structured-tools-runs.md) |
| Lookup CTI reale | [owl-cti-integration.md](docs/owl-cti-integration.md), [cti-workforce.md](docs/cti-workforce.md) |
| Applicabilità Ubuntu dell'inventario | [ubuntu-package-applicability.md](docs/ubuntu-package-applicability.md) |
| MCP strategico | [mcp-strategic.md](docs/mcp-strategic.md) |
| OpenTelemetry | [opentelemetry-integration.md](docs/opentelemetry-integration.md) |
| SBOM/OSV | [sbom-osv-integration.md](docs/sbom-osv-integration.md) |
| Applicazione osservata | [observed-app-integration.md](docs/observed-app-integration.md), [observed-app-ollama.md](docs/observed-app-ollama.md) |
| Correzioni e inferenze successive | [ollama-contract-tests.md](docs/ollama-contract-tests.md), [agent-tool-phases.md](docs/agent-tool-phases.md) |
| Fonti e scelte | [fonti-e-scelte.md](docs/fonti-e-scelte.md), [bibliografia.bib](docs/riferimenti/bibliografia.bib) |

La formula del ranking mock non va attribuita automaticamente al BWAF della
baseline o a un paper. Per spiegarla occorre riferirsi al codice e alle scelte
documentate, distinguendo euristica del prototipo e algoritmo esterno.

## 4. Caso Apache: fonti e decisioni

La ricognizione ha individuato l'export
`opentelemetry/data/otel-zenodo-logs.json` nel primo repository esterno.
Contiene tre messaggi `AH00163` di avvio `mpm_prefork` con
`Apache/2.4.29 (Ubuntu)`.

I messaggi sono stati confrontati con i file originali dell'
[AIT Log Data Set V2.0](https://zenodo.org/records/5789064), scenario
`russellmitchell`, host `webserver`. Sono stati recuperati selettivamente sei
file dell'archivio, evitando il download integrale. I tre messaggi coincidono
esattamente con le righe dei log originali; sono conservati hash, puntatori e
manifest. I facts identificano Ubuntu 18.04 e il pacchetto
`apache2 2.4.29-1ubuntu4.21`.

Decisioni fondamentali:

- Il dataset è uno scenario sperimentale pubblicato con attività simulate,
  non la prova di un incidente in produzione.
- Leggere oggi l'export non rende la raccolta live: il profilo è `recorded`.
- Nome e versione osservati (`Apache`, `2.4.29`) rimangono separati dalla
  versione inventariale Ubuntu (`2.4.29-1ubuntu4.21`).
- I facts sono successivi agli eventi: non attestano lo stato delle patch
  in ciascun istante storico.
- L'etichetta `dataset:russellmitchell:webserver:apache2` identifica l'ambito
  del dataset; non è un identificatore di istanza dichiarato dal runtime.
- I facts non sono una SBOM di build. Per Apache non viene riutilizzata la
  SBOM Maven dell'altra applicazione; l'ingresso SBOM/OSV è disabilitato nel profilo.

Il gateway controlla hash e corrispondenza esatta delle righe, estrae la versione
dal messaggio supportato e pubblica un contesto registrato distinto. L'LLM non
deve ricostruire o modificare quei dati.

Implementazione: `services/otel_gateway/apache_recorded.py`, estensioni di
`server.py`, `thesis_agents/schemas/telemetry_source.py`,
`thesis_agents/tools/telemetry_http.py` e delle spiegazioni finali.
Configurazioni: `config/backends.otel-apache-cti.json` e
`config/input.otel-apache-recorded.json`.

Dettagli e riproduzione: [verifica delle fonti](docs/baseline-apache-verification.md)
e [integrazione Apache](docs/apache-recorded-integration.md).

## 5. Risultati effettivamente verificati per Apache

Il collaudo completo è conservato in `output/apache-recorded-integration/`:

- 1.109 record letti; tre avvii Apache riconosciuti e selezionati;
- gateway HTTP e CTI reale via MCP, con quattro agenti CAMEL;
- modello programmato di test, nessuna inferenza Ollama;
- query letterale `Apache`, versione `2.4.29`: `lookup_status=no_match`;
- decisione `insufficient_evidence`, strategia `null`;
- completamento degli artefatti e lettura separata delle tre evidenze da parte
  dello Strategic, verificata in `strategic_context.json`.

Il precedente probe con nome interpretato `Apache HTTP Server` restituiva
invece identità ambigue. Le valutazioni upstream grezze non erano pubblicate
come finding dell'applicazione. `no_match`, `ambiguous`, `no_findings` e
`insufficient_evidence` non sono sinonimi: assenza di correlazione o informazioni
insufficienti non dimostrano assenza di vulnerabilità.

Al completamento dell'incremento Apache: **281 test passati**, Ruff e
`git diff --check` superati. Questi controlli precedono i nuovi file del resolver.

## 6. Resolver CTI: incremento isolato concluso

È stato aggiunto un tool MCP separato, **`resolve_software_identity`**, con
contratto **`cti-identity-resolution-v1`**. Il client invia il nome osservato e
il contesto registrato; il server esegue la normalizzazione esplicita e conserva
sia la richiesta originale sia il risultato grezzo della ricerca normalizzata.

La regola supporta il caso Apache registrato e richiede contesto coerente:
servizio `apache2`, host `webserver`, inventario Ubuntu della stessa versione
upstream, riferimenti e hash delle fonti. Non è un resolver generale.

Nella v1 tre identità sono state esaminate come equivalenti nello specifico snapshot:

| Identità CTI | Entry esaminate |
|---|---:|
| `apache software foundation::apache http server` | 106 |
| `n a::apache http server` | 9 |
| `apache::apache http server` | 5 |

La regola conserva dataset hash, elenco delle CVE e riferimento alla
[pagina ufficiale Apache HTTP Server 2.4](https://httpd.apache.org/security/vulnerabilities_24.html),
sulla quale sono stati riscontrati gli identificativi esaminati. È una regola
curata del prototipo: non è un algoritmo tratto da un paper e non consente di
trattare genericamente ogni vendor `n/a` come Apache. L'appartenenza delle CVE
al progetto non dimostra la vulnerabilità del pacchetto Ubuntu osservato.

Il dataset è vincolato allo SHA-256:

```text
e3566009408385c7aea7901a9e6499132f0ae4bb07ccbd80d22e2171e5f7990c
```

Il risultato distingue candidate `equivalent`, `excluded` e `unresolved`;
mantiene alternative e motivazioni. `package_applicability` rimane
**`not_assessed`**. Hash e riferimenti inviati dal client sono controlli di
coerenza, non un'attestazione remota dell'autenticità delle fonti.

### File aggiunti

In `tesi`:

- `thesis_agents/mcp/identity_contracts.py`: contratto pubblico Pydantic;
- `thesis_agents/mcp/identity_probe.py`: client di collaudo isolato, audit e output;
- `tests/test_cti_identity.py`: test sintetici dei controlli client.

Nel repository esterno, soltanto file nuovi:

- `app/src/cti_mcp/identity_contracts.py`;
- `app/src/cti_mcp/identity_service.py`;
- `app/src/cti_mcp/identity_server.py`;
- `app/src/cti_mcp/apache_identity_rules.json`;
- `app/tests/cti_mcp/test_identity.py`.

I file preesistenti del backend, incluso il matcher, non sono stati modificati
in questo incremento. Le copie preparatorie sono in
`output/cti-identity-development/`, ma il servizio usa i file del repository
esterno. Il contratto client è una copia pubblica, non un import del backend.

### Prima prova reale e correzione successiva

Il probe in `output/apache-identity-resolution/` ha attraversato MCP HTTP
con il database reale. Esito: **`ambiguous`**, gruppo e selezione assenti,
`package_applicability=not_assessed`. Non è una prova Workforce o LLM.

La ricerca ampliata ha restituito 20 candidate, raggiungendo il limite del
nuovo endpoint. Ha inoltre fatto emergere `apache::http_server`, con sei entry.
Il limite raggiunto impedisce al resolver di dichiarare una risoluzione
completa; la presenza dell'ulteriore alias richiede revisione.

**Attenzione al risultato storico:** nella prima risposta salvata
`apache::http_server` è classificato `excluded`. È stata poi corretta la regola:
un candidato con vendor Apache o CPE Apache coerente non viene escluso soltanto
perché ha un nome diverso da `apache http server`; rimane `unresolved`.
La correzione è copiata nel backend, testata e ora **verificata anche tramite
una nuova chiamata MCP al database reale**, conservata separatamente in
`output/apache-identity-resolution-r2/`.

### Secondo probe reale e chiusura

Il secondo probe conferma `ambiguous`, gruppo `null`, selezione vuota e
`package_applicability=not_assessed`. Le 20 candidate sono tre `equivalent`,
sedici `excluded` e una `unresolved`: `apache::http_server`, con sei entry.
Il limite raggiunto resta dichiarato. Snapshot e richiesta sono identici
alla prima prova, così come la risposta CTI upstream; fra le classificazioni
cambia soltanto l'alias da `excluded` a `unresolved`.

Contratti pubblico/client e backend identici salvo il percorso dell'import
locale; anche il contratto CTI base coincide. I quattro file del servizio
corrispondono alle copie preparatorie. Il repository esterno resta sul commit
di riferimento; alla chiusura della v1 conteneva soltanto i cinque file nuovi
del resolver, senza modifiche ai componenti preesistenti.

Hash del resolver verificato:

```text
a54aef4e82b67e5eeea3604c48e19714fe283a52380df0ccc2f9f0b72aa62682
```

Hash della regola, invariata:

```text
3485679139a0b8b0a252613d0506f5dec6c963bb97dd57de642327dce2fd0da1
```

Controlli completati per l'incremento v1:

| Controllo | Risultato |
|---|---|
| Suite MCP del backend esterno, inclusa regressione sull'alias | **33 passed** |
| `tests/test_cti_identity.py` nel client | **13 passed** |
| Ruff su tutto `tesi` | **Superato**, F811 corrette |
| Formato dei tre file client del resolver | **Superato** |
| Suite completa di `tesi` dopo i nuovi file | **294 passed** |
| Probe reale dopo la correzione | **Validato**, identità `ambiguous` |
| `git diff --check` | **Superato** |

Le fixture sintetiche sono ora riusate tramite i rispettivi moduli, evitando
le collisioni F811 con i parametri pytest. Dati dei test e logica del resolver
non sono cambiati. Le prove HTTP richiedono i permessi per aprire socket locali;
la suite backend ha inizialmente incontrato due errori di permesso del sandbox,
poi è passata integralmente con il loopback consentito.

Il server temporaneo del resolver su porta 8005 è stato arrestato. Non
considerare attivo un endpoint solo perché compare nei file di configurazione.

### Incremento v2: revisione degli alias e copertura lessicale

L'incremento successivo è documentato nella
[guida v2](docs/cti-identity-resolution-v2.md). La ricerca completa secondo
il metodo della baseline ha fatto emergere due ulteriori forme del nome
HTTP Server e tre prodotti Apache distinti. Per le nove entry dei tre alias
aggiuntivi sono stati verificati record pubblici CVE: CNA Apache con prodotto
HTTP Server, percorso ADP, vendor/prodotto e CPE corrispondenti al database.
Sono conservati snapshot, hash e revisione in
`output/cti-identity-r3-development/`.

Le nuove identità equivalenti sono:

| Identità CTI | Entry |
|---|---:|
| `apache::http_server` | 6 |
| `apache_software_foundation::apache_http_server` | 2 |
| `apache::apache_http_server` | 1 |

Le tre identità della v1 rimangono equivalenti. Confidence e punteggi del
matcher sono conservati, anche `needs_review` per i tre alias; l'equivalenza
è giustificata dalla regola curata e non promuove le valutazioni upstream.
Airflow Providers Http, Camel Platform HTTP Main e Felix HTTP Webconsole
Plugin sono esclusi esplicitamente sulla base dei rispettivi record CNA.
Le regole vincolano tutte le identità esaminate anche all'hash delle entry,
inclusi ID, IRI, percorsi e CPE. Non viene introdotta un'equivalenza generica
per vendor Apache o `n/a`.

La ricerca usa il matcher preesistente con limiti derivati dalle 81.988
identità utilizzabili dell'indice: limite finale 81.989 e limite per token
409.945. Le candidate generate sono 220, di cui 107 eliminate dalla policy
del matcher come `no_match`; le 113 restituite rimangono tutte visibili.
Il resolver classifica queste ultime in sei equivalenti e 107 escluse.
`complete=true` riguarda solo la ricerca esatta/per token prevista dalla
baseline, senza ricerca vettoriale o promessa di copertura semantica globale.

Il contratto additivo è `cti-identity-resolution-v2`, con selezione esplicita
`--contract v2` nel probe; il default v1 rimane disponibile. La risposta
conserva il lookup upstream originale v1 a 20 risultati e aggiunge `search`,
con risultato lessicale completo, conteggi e hash. I contratti client/backend
v2 coincidono salvo l'import locale. I file v1 e i componenti versionati
della baseline restano invariati.

File aggiunti nel backend: `identity_v2_contracts.py`, `identity_search.py`,
`identity_v2_service.py`, `identity_v2_server.py`, `apache_identity_rules_v2.json`
e `app/tests/cti_mcp/test_identity_v2.py`. Nel client: contratto pubblico
`thesis_agents/mcp/identity_v2_contracts.py`, test `tests/test_cti_identity_v2.py`
ed estensione compatibile di `identity_probe.py`.

Il probe MCP reale in `output/apache-identity-resolution-r3/` conclude con
`resolved`, gruppo `apache:http_server`, sei identità selezionate e
`package_applicability=not_assessed`. Snapshot e richiesta sono identici
byte per byte a r2; il lookup upstream originale coincide. L'audit e una
verifica separata conservano queste corrispondenze e il rifiuto client di
candidate mancanti, applicabilità inventata, ambiguità nascosta e falsa copertura.

Hash della regola v2:

```text
f1edde46dd88ca305f3dc7974e6e1bb5c5e6869f6d71e9cc4367507a2d1d6402
```

Controlli alla chiusura della v2: **308 passed** nella suite completa del prototipo,
**40 passed** nella suite MCP backend, Ruff e formato dei file modificati
superati. Il servizio temporaneo v2 è stato arrestato. Non sono state fatte
inferenze LLM o esecuzioni Workforce in questo incremento, né commit o push.

### Valutazione Ubuntu: incremento isolato concluso

Il tool MCP additivo `assess_ubuntu_package`, contratto
`ubuntu-package-assessment-v1`, usa record dell'API Ubuntu fissati con hash,
facts originali e notice `USN-5212-1`. La
[guida dedicata](docs/ubuntu-package-applicability.md) documenta regole,
fonti, prove e limiti. La revisione completa `2.4.29-1ubuntu4.21` viene
confrontata con le soglie Ubuntu mediante `python-debian==1.0.1`;
non viene confrontato soltanto il banner upstream.

Il servizio controlla che `apache2` e `apache2-bin` risultino alla stessa
revisione nei facts e che i metadati del notice associno quei binari al source
package `apache2`. Controlla inoltre hash e tempo dell'inventario, identità
risolta e corrispondenza della revisione CTI/regola con il manifest delle fonti.
Il client non importa il backend o il comparatore e non legge i suoi dati.

Tutti i 120 record Ubuntu sono disponibili. Il probe definitivo in
`output/ubuntu-apache-applicability-r2/` restituisce:

| Esito | CVE |
|---|---:|
| `fixed`: inventario uguale o successivo al fix Ubuntu | 34 |
| `not_affected`: esclusione Ubuntu per il pacchetto/release | 28 |
| `potentially_affected`: sotto soglia oppure problema aperto | 46 |
| `unknown`: record presente senza stato Bionic | 12 |

Esempi: `CVE-2021-44224` e `CVE-2021-44790` sono corrette proprio dalla
revisione `.21`, come attestano notice e changelog ufficiali;
`CVE-2022-22720` è potenzialmente applicabile perché corretta in `.22`;
`CVE-2024-38472` è esclusa da Ubuntu perché specifica di Windows.

I 12 casi indeterminati sono CVE del 2016–2017 senza uno stato Bionic nei
record acquisiti. Non sono errori di download né esclusioni implicite.
Le versioni sotto soglia restano potenziali perché non sono verificati il
momento d'introduzione del difetto, moduli/configurazione ed esposizione.
La conoscenza attuale del tracker viene applicata retrospettivamente:
non ricostruisce la CTI nota nel gennaio 2022.

La risposta incorpora il risultato d'identità originale e conserva una riga
per ogni CVE unica, con tutti gli alias d'origine, URL/hash e puntatori agli
stati Ubuntu. Il campo `package_applicability=not_assessed` dentro il risultato
d'identità rimane invariato: la valutazione del pacchetto è un risultato separato.
Restano `runtime_applicability=not_assessed` e `historical_runtime_state=not_established`.

La prima prova in `output/ubuntu-apache-applicability/` è conservata: aveva
tre esiti `unknown` aggiuntivi perché il comparatore accettava note
`windows-specific` come versioni legacy. Sono stati aggiunti un vincolo
sintattico Debian e tre regressioni. Il probe r2 usa gli stessi snapshot;
cambiano solo quei tre casi, ora correttamente `not_affected`.
`verification.json` conserva la corrispondenza di snapshot/identità e il rifiuto
client di conteggi, inventario, fonti o affermazioni runtime alterati.

Snapshot del servizio: `output/ubuntu-apache-sources/manifest.json`, SHA-256:

```text
6e11b205b3e465d1afe5ac5757679af0f612a31530c060f148732d50a289af62
```

Le acquisizioni e le copie preparatorie dei nuovi file sono in
`output/ubuntu-applicability-development/`. Nel backend sono stati aggiunti
`ubuntu_contracts.py`, `ubuntu_sources.py`, `ubuntu_service.py`,
`ubuntu_server.py`, `requirements-ubuntu.txt` e `app/tests/cti_mcp/test_ubuntu.py`.
Nel prototipo sono aggiunti contratto pubblico, `ubuntu_probe.py` e i test
client. I componenti preesistenti, i resolver e i log restano invariati.
La dipendenza opzionale `python-debian` è installata nella `.venv` locale
e dichiarata nel file dei requisiti del nuovo servizio, senza import client.

Verifiche finali: **320 passed** nel prototipo e **69 passed** nel backend,
Ruff, formato, `git diff --check`, contratti sincronizzati e `pip check`
superati. Il server temporaneo sulla porta 8006 è stato arrestato.
Nessuna inferenza LLM, nuova esecuzione Workforce, modifica della relazione,
commit o push in questo incremento.

### Collegamento al VulnerabilityAgent concluso

L'adapter `thesis_agents/tools/ubuntu_mcp.py` usa i soli contratti pubblici.
`schemas/ubuntu.py` definisce la sintesi con tutti gli ID CVE raggruppati,
conteggi, inventario, copertura e riferimenti verificabili. La sessione passa
evidenza e snapshot verificati al backend, conserva la risposta immutabile
e ricostruisce la sintesi prima di pubblicare e concludere il run.
La provenienza include `ubuntu_package_assessment` e le dipendenze da
runtime evidence e snapshot OTel. Gli schemi esposti agli agenti dipendono
dall'adapter; quelli precedenti non inglobano lo schema Ubuntu completo.

Il collaudo reale in `output/apache-ubuntu-workforce/` verifica una sola
chiamata di dominio MCP, sei alias conservati e risultati per CVE identici
al probe `ubuntu-apache-applicability-r2`. Il report è di 6.105 byte contro
813.881 della risposta integrale, senza perdere i 120 ID. Sono misure di
file JSON, non token LLM. `verification.json` controlla digest, hash della
provenienza, puntatori della spiegazione, contesto strategico e risultati.
I warning gestionali CAMEL derivano dal modello programmato che non valuta
la qualità dei task; il fallback a 80 non misura un LLM.

I test hanno individuato e risolto una regressione nei contratti v1: il
bridge `legacy_payload` elimina il nuovo campo solo quando nullo e rifiuta
evidenze Ubuntu presenti. Gli schemi wire v1 restano invariati. I nuovi test
verificano mapping, quattro verdetti, assenza di promozioni runtime anche
con tutte le CVE corrette, pubblicazione immutabile, dati alterati, pin,
cache, passaggio CAMEL e provenienza. Nessun codice del backend esterno
è stato modificato; nessuna inferenza Ollama è stata eseguita qui.
La suite completa finale conclude con **336 passed**; sono superati Ruff,
formato, `pip check` e `git diff --check`. I 69 test backend restano il
risultato dell'incremento precedente, non una nuova esecuzione.
Gateway e servizio MCP temporanei sulle porte 8004 e 8006 sono stati arrestati
al termine del collaudo. Nessun commit o push effettuato.

### CountermeasureAgent Ubuntu concluso

`schemas/verification.py` definisce richieste pendenti e contesto con digest.
`tools/package_verification.py` prepara una lista deterministica dai quattro
verdetti già pubblicati. Il Countermeasure invoca `prepare_package_verification`
e pubblica `CandidateStrategies.verification_requests`, separato da `strategies`.
La sessione richiede tutte le richieste senza modifiche, verifica il contesto
immutabile prima delle pubblicazioni e nelle letture successive e lo include
nella provenienza come preparazione invocata dal CountermeasureAgent.
Non vi sono nuove query SBOM/OSV o acquisizioni runtime.

Il run `output/apache-ubuntu-countermeasure/` contiene:

- `historical_runtime_state`: 58 CVE, per revisione effettiva del processo,
  riavvii e riconciliazione fra log del 22–24 gennaio e inventario del 25 gennaio;
- `runtime_conditions`: 46 CVE potenziali, per prerequisiti specifici dalle
  fonti, moduli caricati, configurazione e raggiungibilità;
- `ubuntu_status`: 12 CVE indeterminate, per fonti ufficiali specifiche Bionic;
- `upgrade_compatibility`: 46 CVE potenziali, per percorso supportato,
  disponibilità, dipendenze, moduli, applicazione, manutenzione e rollback.

I gruppi si sovrappongono: sono 58 CVE uniche. Le 34 corrette e le 28
non applicabili sono escluse dall'insieme di indagine pendente. Nessuna
versione di upgrade è stata scelta. Lo Strategic riporta i controlli aperti
nella spiegazione derivata dagli artefatti; grafo e ranking considerano solo
le strategie, quindi restano vuoti insieme alle validazioni. La decisione è
ancora `insufficient_evidence`. I risultati per tutte le 120 CVE coincidono
con il run precedente; hash della provenienza e puntatori sono verificati
in `output/apache-ubuntu-countermeasure/verification.json`.

Suite finale **350 passed**, inclusi 14 nuovi test di copertura, integrità,
omissioni, dati inventati, compatibilità legacy e passaggio CAMEL. Ruff,
formato, `git diff --check` e `pip check` superati. Il nuovo payload richiede
copia esatta delle richieste; una prova Ollama dovrà verificare budget di
contesto e risposta. Nessuna inferenza LLM, verifica infrastrutturale,
mitigazione, modifica al backend esterno, commit o push in questo incremento.

### StrategicAgent: ramo Apache senza candidate concluso

La nuova configurazione seleziona `strategic_adapter=empty-evidence-v1`.
`services/strategic_gateway/server.py` espone un servizio MCP separato:
`rank_graph` restituisce astensione soltanto su grafo vuoto e rifiuta grafi
non vuoti; `record_provenance` e `read_provenance` scrivono e rileggono
record JSON ed export JSON-LD. Non usa gli algoritmi mock per classificare
strategie e non invoca BWAF, Tiny-ME o Fabric. Il backend semantico resta
configurato mock ma non viene chiamato in questo ramo.

`tools/evidence_strategic_mcp.py` verifica le risposte MCP, il binding della
ricevuta e il contenuto riletto, senza accesso ai file del server. La sessione
ricontrolla copie locali, ricevuta e derivazione nell'audit finale.
`provenance.py` esporta entità, attività e agenti con IRI distinti per run,
usando relazioni PROV-O e proprietà applicative per hash e nomi dei file.
RDFLib è aggiunto soltanto alle dipendenze di sviluppo, con pin nel lock:
i test leggono l'export come RDF e verificano relazioni e hash.

Il run `output/apache-ubuntu-strategic/` conserva quattro chiamate validate:
valutazione Ubuntu, astensione, scrittura del record, rilettura. La verifica
confronta tutte le CVE e richieste con il run precedente, archivio server,
copie client, puntatori, file e RDF. Risultati in `verification.json`;
ricevuta ed export nei sidecar `provenance_receipt.json` e `provenance.jsonld`.
Non sono inclusi nel record che descrivono, evitando autoriferimenti.

La baseline strategica ispezionata è alla revisione
`a3dab4a5def79dda356dd753aa34306e03ea346a`. `StoreGraph` richiede nodi e archi
non vuoti; il formato nativo non rappresenta direttamente pesi e tipi di
relazione del prototipo. Le API Tiny-ME operano su ontologie e individui,
non sul nostro `DecisionContext` JSON. Restano necessari mapping e contratti
specifici. La verifica finale non raggiunge Docker né Fablo REST su 8800;
nessun endpoint alternativo è stato fornito. Fonti e hash ispezionati in
`output/apache-ubuntu-strategic/baseline-readiness.json`. Nessun repository
esterno è stato modificato, né sono state inviate transazioni.

Suite finale **370 passed**, con 20 nuovi test di export RDF, astensione,
archivio immutabile, risposte alterate, contratti e CAMEL. Ruff, formato,
`pip check` e `git diff --check` superati. Nessuna nuova inferenza Ollama,
mitigazione, commit o push. La chiusura riguarda il ramo senza candidate;
non dichiarare completata l'integrazione complessiva BWAF/Tiny-ME/Fabric.
I servizi temporanei OTel, CTI Ubuntu e strategico sulle porte 8004, 8006
e 8007 sono stati arrestati dopo il collaudo.

### Prova completa Apache con Ollama effettivo

È completato il primo run LLM del nuovo percorso Apache, distinto dal
precedente collaudo con `ScriptedToolModel`. Profilo e fonti sono quelli
già verificati: OTel 8004, Ubuntu MCP 8006, servizio strategico 8007.
È stato creato un alias locale `tesi-apache-qwen3:4b-32k` dai pesi già
installati di `tesi-qwen3:4b`, con `num_ctx=32768`, senza modificare
l'alias precedente o scaricare nuovi pesi. `.env` e chiavi cloud non usati
per l'inferenza: endpoint e credenziali fittizie locali sono espliciti.

`tests/support/apache_ollama_run.py` avvia la CLI effettiva in un processo,
conserva manifest, sorgenti con hash, stato Ollama, conversazioni SDK e
risultati anche falliti. `apache_ollama_audit.py` controlla in sola lettura
contratti, consegna degli input, derivazioni, hash, spiegazione, ricevuta
e lettura RDF. Nessun artefatto è completato a mano.

- **r1**, `output/apache-ollama-20261018-r1/`: fallito dopo 593,92 s,
  17 richieste registrate. Telemetry e Vulnerability pubblicano correttamente.
  Countermeasure scrive due pseudo-chiamate come testo, non pubblica il
  proprio artefatto; la sessione rifiuta il successo e blocca Strategic.
- **Correzione**: `CountermeasureToolPolicy`, selezionata per i backend che
  richiedono contesto runtime verificato. Espone un tool per fase e obbliga
  ogni clone a rileggere il contesto. Testo ed errori non avanzano lo stato;
  la policy non genera payload o pubblicazioni. Sei regressioni sincrone e
  asincrone verificano cloni, testo, rifiuti e tool fuori fase.
- **r2**, `output/apache-ollama-20261018-r2/`: completo, audit passato,
  1.284,92 s. 28 richieste registrate: Telemetry 4, Vulnerability 4,
  Countermeasure 7, Strategic 8, gestione 5; 26 risposte, due timeout.
  Countermeasure ha ancora un payload scritto come testo nel primo tentativo,
  poi va in timeout; il retry pubblica tramite il tool reale. Strategic
  pubblica decisione e provenienza ma il seguito gestionale va in timeout;
  il retry rilegge quanto già valido e conclude.

Non ci sono risposte terminate per limite di generazione. Massimo prompt
riportato 20.064 token; somma riportata 231.278 prompt e 10.629 completamento.
Sono conteggi con cronologie ripetute/cache, non token unici o costi API.
Prima di r1 nessun modello era residente, prima di r2 il modello era già
residente; in r2 la suite test è stata eseguita in parallelo. Non presentare
le due durate come benchmark controllato o i run come una stima statistica.

Tutti i risultati CVE, gli alias e le fonti coincidono con il collaudo
programmato; le quattro richieste sono conservate integralmente. L'audit
verifica 143 triple nel grafo RDF e la rilettura MCP dell'archivio.
`comparison.json` conserva il confronto, `audit.json` gli esiti. Il commento
LLM resta non verificato: espressioni come «no identified vulnerabilities»
possono essere ambigue rispetto ai casi potenziali; la spiegazione derivata
distingue esplicitamente finding, stato del pacchetto e richieste pendenti.

Suite completa **376 passed**, inclusi sei test della nuova policy;
Ruff e `git diff --check` superati. Nessun nuovo finding runtime, mitigazione,
BWAF/Tiny-ME, Fabric, modifica ai backend esterni, commit o push.
I servizi temporanei 8004/8006/8007 sono stati arrestati; Ollama preesistente
rimane attivo e l'alias locale è conservato per riproduzione. Verbale in
`output/apache-ollama-20261018-r2/cleanup.json`.

## 7. Ripresa operativa dopo la prova Ollama Apache

Non ripetere da zero download, prove già concluse o inferenze costose.
La [guida Ubuntu](docs/ubuntu-package-applicability.md) documenta il nuovo
servizio; la [guida v2 del resolver](docs/cti-identity-resolution-v2.md) e
quella v1 conservano contratti e risultati precedenti.
È collegata da README, piano MCP e guida Apache. I servizi temporanei non
vanno considerati attivi soltanto perché compaiono nelle configurazioni.

1. Controllare lo stato dei due repository, preservando modifiche e output storici.
2. Usare il profilo `backends.otel-apache-ubuntu.json` per il nuovo percorso;
   il profilo precedente conserva il confronto con il lookup letterale.
   Per astensione e archivio PROV-O remoto usare invece
   `backends.otel-apache-strategic.json`, con servizio MCP sulla porta 8007.
3. Acquisire evidenze delle condizioni runtime prima di presentare i casi
   potenziali come finding confermati; approfondire le 12 assenze di stato Bionic.
4. Per una prova Ollama, verificare prima il budget di contesto e risposta:
   le pubblicazioni conservano i 120 ID e le richieste complete di verifica.
   La prima prova completa è ora disponibile in r2; evitare di ripeterla
   identica senza un'ipotesi su robustezza, timeout o costo della copia.
5. Integrare uno alla volta i servizi reali dello StrategicAgent, partendo
   dai contratti e da un collaudo isolato. Le verifiche pendenti non sono
   strategie da inserire nel ranking.

Per avviare il servizio Ubuntu, dalla radice del repository esterno:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=app/src \
  /Users/reucalion/tesi/.venv/bin/python -m cti_mcp.ubuntu_server \
  --sqlite app/data/cve2owl_20260523_143950.affected.sqlite \
  --dataset-id cve2owl_20260523_143950 --dataset-kind real \
  --sources /Users/reucalion/tesi/output/ubuntu-apache-sources/manifest.json --port 8006
```

Dalla radice di `tesi`, con snapshot già disponibile e output nuovo:

```sh
.venv/bin/python -m thesis_agents.mcp.ubuntu_probe \
  --url http://127.0.0.1:8006/mcp \
  --snapshot output/apache-recorded-integration/artifacts/telemetry_snapshot.json \
  --output-dir output/ubuntu-apache-applicability-r3 \
  --expected-kind real \
  --dataset-sha256 e3566009408385c7aea7901a9e6499132f0ae4bb07ccbd80d22e2171e5f7990c \
  --sources-sha256 6e11b205b3e465d1afe5ac5757679af0f612a31530c060f148732d50a289af62
```

Controlli del progetto principale:

```sh
.venv/bin/python -m pytest -q
.venv/bin/ruff check .
git diff --check
```

Controlli del backend, dalla sua radice:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=app/src \
  /Users/reucalion/tesi/.venv/bin/python -m pytest -q \
  -p no:cacheprovider app/tests/cti_mcp
```

Le modifiche al repository esterno richiedono i permessi previsti dall'ambiente;
l'utente ha già autorizzato le aggiunte per questa integrazione. Non estendere
implicitamente tale autorizzazione a riscritture dei componenti preesistenti.

## 8. Lavoro successivo, non ancora realizzato

- Estendere in futuro la risoluzione ad altri contesti o alias soltanto con
  nuove regole e copertura dichiarata; il caso Apache registrato è collaudato in v2.
- Approfondire i 12 casi senza stato Bionic e le condizioni runtime dei
  46 casi potenziali; la valutazione isolata dell'inventario è già collaudata.
- Il collegamento Vulnerability è completato; il vecchio profilo con lookup
  letterale `no_match` rimane disponibile per confronto storico.
- Il Countermeasure è adattato: le richieste pendenti sono pubblicate e
  tracciate; la loro esecuzione e l'acquisizione delle evidenze restano aperte.
- Valutare un inventario/SBOM coerente con il caso Apache e il relativo supporto
  OSV, senza riutilizzare il contratto Maven come se descrivesse pacchetti Ubuntu.
- Eseguire una prova Ollama sul nuovo caso solo quando gli ingressi e il loro
  significato sono definiti: r1 e r2 sono ora conservati, con r2 verificato.
  Rimangono ripetizioni controllate, riduzione dei payload di copia e timeout.
- Integrare separatamente Semantic Validation SC, Argumentation SC, audit
  Fabric. L'export PROV-O è realizzato e verificato come RDF; il nuovo profilo
  usa astensione MCP e archivio reale su file, senza questi smart contract.
- L'applicazione effettiva delle mitigazioni e il feedback runtime restano
  distinti dalla sola selezione di una strategia.

## 9. File da preservare e documentazione destinata al professore

Il working tree di `tesi` contiene anche modifiche precedenti a questo
incremento. In particolare sono modificati `docs/materiali/relazione.docx`,
`docs/materiali/README.md`, README e piano MCP; sono presenti
`docs/materiali/integrazione-relazione.md` e il file temporaneo Word
`docs/materiali/~$lazione.docx`. Non cancellarli o sovrascriverli durante la
pulizia del lavoro CTI. Il documento Word contiene interventi dell'utente.

Per la relazione l'utente ha chiesto di continuare il testo esistente, senza
sovrascriverlo, con stile uniforme e senza date o riferimenti a formati di file
non necessari. Un'eventuale rigenerazione del PDF deve partire dalla versione
che contiene effettivamente le modifiche dell'utente, non da un Markdown
potenzialmente precedente. La nuova attività CTI non è ancora stata riportata
come incremento concluso nella relazione.

Gli output sotto `output/` sono locali e normalmente esclusi da Git. Non
eliminarli prima di aver conservato le evidenze necessarie; un clone nuovo
non li contiene. I riferimenti bibliografici alle baseline conservano revisioni
storiche: non confonderle con l'HEAD attuale.

## 10. Testo breve per iniziare la nuova chat

> Leggi `resoconto.md` nella radice di `/Users/reucalion/tesi` e controlla lo
> stato dei repository prima di modificare file. Identità Apache v2 e valutazione
> Ubuntu sono integrate nel VulnerabilityAgent e nella Workforce tramite
> config/backends.otel-apache-ubuntu.json. Il run apache-ubuntu-workforce conserva:
> 34 fixed, 28 not_affected, 46 potentially_affected e 12 unknown.
> Il collaudo CAMEL usa inferenza programmata, servizi OTel/MCP reali e tool
> strategici mock. Nessuna nuova prova Ollama; il backend esterno è invariato.
> Il Countermeasure è ora adattato: apache-ubuntu-countermeasure pubblica quattro
> richieste pendenti su 58 CVE uniche, distinte dalle strategie. Non sono eseguite.
> Il nuovo profilo backends.otel-apache-strategic.json conclude il ramo senza
> candidate: astensione MCP esplicita e archivio PROV-O con rilettura verificata.
> Run apache-ubuntu-strategic: 120 CVE e quattro richieste conservate, nessuna
> strategia scelta, ledger_status=not_submitted. Suite finale: 370 test superati.
> La prova con Ollama effettivo è ora conclusa: apache-ollama-20261018-r1
> fallisce nel Countermeasure, r2 supera l'audit dopo una policy per fasi.
> R2 dura 1.284,92 s con 28 richieste e due retry per timeout; non è affidabile
> senza recuperi. Sorgenti e conversazioni conservati. Suite aggiornata: 376 test.
> BWAF/Tiny-ME/Fabric restano aperti: Docker/Fablo non disponibili e mapping
> semantico non validato. Non dichiararli integrati. Runtime e processo storico
> restano non verificati; non promuovere richieste o casi potenziali a finding.
> Preserva le modifiche alla relazione e i componenti preesistenti delle baseline.

## 11. Porting selettivo principe-thesis su costa-thesis

Aggiornamento del 30 ottobre 2026: su richiesta dell'utente, dopo la verifica
in sola lettura, sono stati importati i servizi condivisi nelle due copie locali
dei repository esterni, entrambe rimaste su `costa-thesis`. Nessun commit o push.

- `agent-based-cti-argumentation-pipeline`: bridge MCP dalla revisione
  `441013262cf2247a7f6f4c6659b2761e7d53a8d6`, inclusi i tool di dominio.
- `semantic-cti-ledger-argumentation`: backend `fablo-rest` dalla revisione
  `023b7118d1dcd3814a2dd9ebb0fe438a8158e315`, contratti, servizi e test.
- Preservati file Identity/Ubuntu preesistenti, credenziali e rete; nessuna
  modifica alla pipeline Python. Corretti build, dipendenze e collisioni degli
  identificativi di grafi/decisioni. Sorgenti SaaS resi tracciabili in Git.
- Nella copia isolata: compilazione dei due componenti riuscita, handshake MCP
  con 19 tool e 66 test Jest passati in 13 suite. Fabric e simulato nei test.
- Il framework MAS non e ancora collegato al bridge condiviso. Restano binding
  dei chaincode, argomenti/risposta di ExplainAffinity, configurazione TLS,
  commit/rilettura effettivi e provenance della raccomandazione dry-run.
- Dashboard Grafana e casi di argumentation sono gia presenti su costa-thesis;
  il modulo LLM di generazione annotazioni/argomenti resta da identificare.

Dettagli in `docs/porting-principe-costa.md`; patch, backup, manifest con hash e
risultati dei controlli in `output/porting-principe-costa-20261030/`.
Questo aggiornamento sostituisce le precedenti indicazioni sul backend esterno
invariato; non implica che BWAF, Tiny-ME e ledger siano gia collaudati end-to-end.

## 12. Roadmap dopo il porting

Il piano dettagliato e in `docs/prossime-azioni.md`: per ogni fase descrive
interventi, dipendenze e criteri di completamento, considerando anche la proposta
di tesi e le indicazioni successive del professore.

Ordine: consolidare contratti e porting; allineare binding Fabric, ontologia e
ExplainAffinity; collegare il framework al bridge MCP stdio; identificare il
modulo generativo e integrarlo come agente; definire adapter canonico e ranking
atteso; completare selezione e provenance condivisa con commit/rilettura; eseguire
i quattro scenari controllati; collegare la dashboard; misurare correttezza,
ripetibilita e latenza. Nessuna di queste attivita e resa completa dalla sola
redazione del piano. Il prossimo intervento concreto riguarda il backend condiviso.
