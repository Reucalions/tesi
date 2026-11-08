# Resolver CTI Apache: contratto e collaudo isolato

Questa guida conserva il contratto v1 e il risultato storico r2. Il
[successivo incremento v2](../integrazioni/cti-identity-resolution-v2.md) completa la revisione
degli alias e dichiara la copertura lessicale: il probe r3 termina con
`resolved`, mantenendo l'applicabilità Ubuntu `not_assessed`.

Il tool MCP `resolve_software_identity` espone una normalizzazione esplicita
del nome osservato `Apache` verso la query `Apache HTTP Server`. Il collaudo
reale dopo la correzione dell'alias termina con **`ambiguous`**: sono restituite
20 candidate, pari al limite della ricerca, e `apache::http_server` resta
`unresolved`. Il gruppo è `null`, la selezione è vuota e
`package_applicability=not_assessed`.

È concluso l'incremento di contratto, implementazione e verifica isolata.
La risoluzione dell'identità sul dataset reale rimane aperta. Il resolver
non è ancora collegato al VulnerabilityAgent: il
[profilo Workforce Apache](../integrazioni/apache-recorded-integration.md) continua a usare
il lookup letterale, con `no_match` e decisione `insufficient_evidence`.

## Confine fra evidenza, identità e applicabilità

Il client parte dallo snapshot del
[gateway Apache registrato](../integrazioni/apache-recorded-integration.md), senza accedere
al database CTI o importare il codice del backend. Il servizio esterno usa
internamente il matcher preesistente. Il nuovo endpoint aggiunge il tool di
identità e conserva anche `assess_software`; il server CTI precedente rimane
disponibile separatamente.

```text
Snapshot registrato: Apache / 2.4.29 + contesto inventariale e fonti
                 ↓ IdentityRequest via MCP HTTP
Servizio esterno: controllo del contesto → query Apache HTTP Server / 2.4.29
                 ↓ matcher preesistente, massimo 20 candidate
Regola curata: equivalent / excluded / unresolved
                 ↓ IdentityResolution con richiesta e risposta upstream
Probe client: validazione, audit e output; nessuna pubblicazione Workforce
```

La regola supporta esclusivamente il contesto registrato predisposto: nome
`Apache`, versione upstream numerica, nessun vendor dichiarato, base
`recorded-apache-startup`, ambito `dataset-host-service-scope`, host `webserver`,
servizio e pacchetto `apache2`, origine `Ubuntu`. La versione inventariale deve
iniziare con la stessa versione upstream seguita da `-`. Il contratto richiede
anche tempo dei facts, puntatore al record e hash delle fonti e dello snapshot.
Questi hash sono riferimenti forniti dal chiamante: il resolver ne verifica
la coerenza del contratto, senza autenticare a distanza i file originali.

La query normalizzata modifica soltanto il nome del prodotto. Restano
`2.4.29`, l'evidence ID e il vendor assente; `2.4.29-1ubuntu4.21` rimane nel
contesto inventariale. I facts successivi agli eventi non attestano lo stato
delle patch a ciascun istante storico. Le valutazioni upstream restituite
sono dati grezzi e non diventano finding confermati del pacchetto Ubuntu.

## Contratto pubblico e regola curata

Il contratto è `cti-identity-resolution-v1`, definito nel
[modulo pubblico client](../../thesis_agents/mcp/identity_contracts.py). La copia
nel backend è identica salvo il percorso dell'import del contratto CTI base;
anche quest'ultimo coincide fra i due repository. La discovery e la chiamata
MCP effettive hanno verificato la compatibilità degli schemi.

La risposta conserva la richiesta originale con SHA-256, gli hash della regola
e del resolver, la query normalizzata, la risposta upstream integrale e tutte
le candidate restituite nel loro ordine. Ogni candidata include identità,
classificazione, motivazione, numero di entry, CVE e riferimenti. I controlli
client verificano anche il tipo reale/mock del backend, la corrispondenza
della richiesta e l'hash atteso del dataset.

La regola `apache-recorded-identity-v1` è una scelta curata del prototipo,
vincolata allo snapshot CTI:

```text
e3566009408385c7aea7901a9e6499132f0ae4bb07ccbd80d22e2171e5f7990c
```

Le identità esaminate e registrate nella regola sono:

| Identità | Entry | Classificazione nel probe r2 |
|---|---:|---|
| `apache software foundation::apache http server` | 106 | `equivalent` |
| `n a::apache http server` | 9 | `equivalent` |
| `apache::apache http server` | 5 | `equivalent` |
| `apache::http_server` | 6 | `unresolved`, revisione ancora necessaria |

L'equivalenza richiede revisione del dataset, corrispondenza esatta di nome,
vendor e insieme delle CVE, confidence `high` e assenza di CPE in conflitto.
La regola conserva il riferimento alla pagina degli advisory Apache; la
[revisione preparatoria locale](../../output/cti-identity-development/entry-review.json)
e la copia della pagina consultata conservano l'evidenza di quell'esame.
Questo non autorizza ad associare genericamente ogni vendor `n/a` ad Apache
né stabilisce l'applicabilità delle CVE al pacchetto osservato.

Un nome diverso da `apache http server` può essere escluso per somiglianza
lessicale insufficiente soltanto se mancano anche vendor Apache e CPE Apache
coerenti. L'alias `apache::http_server` resta quindi irrisolto e visibile.

| Stato | Significato |
|---|---|
| `insufficient_evidence` | Contesto non supportato; nessuna query normalizzata |
| `unreviewed` | Hash del dataset diverso dalla revisione esaminata |
| `no_match` | Nessuna candidata oppure tutte escluse, senza saturare il limite |
| `ambiguous` | Candidate irrisolte oppure limite della ricerca raggiunto |
| `resolved` | Almeno una candidata equivalente, nessuna irrisolta, limite non raggiunto |

Solo `resolved` può valorizzare il gruppo `apache:http_server` e selezionare
le identità equivalenti. Anche in quel caso `package_applicability` resta
`not_assessed`. Il mancato raggiungimento del limite riguarda la ricerca
eseguita e non dimostra copertura completa di tutta la CTI.

## Riproduzione senza LLM

Sono necessari il backend locale, il database reale e lo snapshot già salvato;
gli output locali non sono inclusi nel clone Git. Per il backend di riferimento
si è verificato il commit `3b483624286262f2e0ac94b4b950b904a5dc2ad4`, con i
cinque nuovi file del resolver ancora non versionati. I componenti preesistenti
non sono stati modificati.

Dalla radice di `agent-based-cti-argumentation-pipeline`:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=app/src \
  /Users/reucalion/tesi/.venv/bin/python -m cti_mcp.identity_server \
  --sqlite app/data/cve2owl_20260523_143950.affected.sqlite \
  --dataset-id cve2owl_20260523_143950 --dataset-kind real --port 8005
```

Dalla radice di `tesi`, scegliere una directory nuova a ogni prova:

```sh
.venv/bin/python -m thesis_agents.mcp.identity_probe \
  --url http://127.0.0.1:8005/mcp \
  --snapshot output/apache-recorded-integration/artifacts/telemetry_snapshot.json \
  --output-dir output/apache-identity-resolution-r2 \
  --expected-kind real \
  --dataset-sha256 e3566009408385c7aea7901a9e6499132f0ae4bb07ccbd80d22e2171e5f7990c
```

Il [probe](../../thesis_agents/mcp/identity_probe.py) rifiuta di sovrascrivere
una directory esistente. Conserva `telemetry_snapshot.json`, `request.json`,
`identity_resolution.json`, `audit.json` e `summary.json`. In caso di errore
conserva richiesta, audit e riepilogo fallito senza pubblicare un risultato
di dominio. Il valore `status=validated` del riepilogo indica il superamento
dei controlli client; l'esito dell'identità è nel distinto `identity_status`.

## Evidenza del secondo probe

Il [riepilogo r2](../../output/apache-identity-resolution-r2/summary.json) e la
[risposta completa](../../output/apache-identity-resolution-r2/identity_resolution.json)
registrano:

- backend e dataset reali, nessun LLM e nessuna esecuzione Workforce;
- 20 candidate: tre `equivalent`, sedici `excluded`, una `unresolved`;
- limite di ricerca raggiunto, `ambiguous`, gruppo `null`, selezione vuota;
- `package_applicability=not_assessed`;
- snapshot copiato byte per byte e richiesta identica al probe precedente;
- risposta upstream identica al probe precedente; fra le candidate cambia
  soltanto `apache::http_server`, da `excluded` a `unresolved`.

Hash SHA-256 del resolver impiegato:

```text
a54aef4e82b67e5eeea3604c48e19714fe283a52380df0ccc2f9f0b72aa62682
```

Hash della regola, invariata rispetto alla prima prova:

```text
3485679139a0b8b0a252613d0506f5dec6c963bb97dd57de642327dce2fd0da1
```

La [prima risposta](../../output/apache-identity-resolution/identity_resolution.json)
rimane conservata come risultato storico: classificava l'alias come `excluded`
e non rappresenta il comportamento corretto attuale. La seconda prova non
aggiunge l'alias alla regola delle equivalenze e non modifica il matcher o i
filtri per ottenere una risoluzione positiva.

## Verifiche e seguito

Le fixture automatiche sono sintetiche; il probe sopra usa il database reale.
I test client verificano conservazione dell'evidenza, rifiuto di risposte
incoerenti, vincolo del dataset e audit anche in caso di errore. I test backend
coprono contesto richiesto, equivalenze, revisioni non esaminate, variazioni
delle entry, CPE in conflitto, saturazione e regressione dell'alias irrisolto.

```sh
.venv/bin/python -m pytest -q
.venv/bin/ruff check .
.venv/bin/ruff format --check thesis_agents/mcp/identity_contracts.py \
  thesis_agents/mcp/identity_probe.py tests/test_cti_identity.py
git diff --check
```

Nel backend, dalla sua radice:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=app/src \
  /Users/reucalion/tesi/.venv/bin/python -m pytest -q \
  -p no:cacheprovider app/tests/cti_mcp
```

Esiti verificati: **294 passed** nel prototipo e **33 passed** nella suite MCP
del backend. Ruff sull'intero prototipo, controllo del formato dei tre file
client del resolver e `git diff --check` superati. Le due segnalazioni F811
sono state corrette riusando le fixture tramite i rispettivi moduli, senza
modificarne i dati o la logica del resolver. I test con socket locali sono
stati eseguiti con i permessi necessari per il loopback. Il servizio temporaneo
sulla porta 8005 è stato arrestato al termine del collaudo.

Il passo successivo è revisionare `apache::http_server` e rendere esplicita
la copertura della ricerca oltre il limite attuale. La valutazione delle
patch Ubuntu e il collegamento al VulnerabilityAgent richiedono incrementi
separati. Nessuna inferenza Apache o mitigazione è stata eseguita in questa prova.
