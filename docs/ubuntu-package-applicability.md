# Applicabilità Ubuntu del pacchetto Apache inventariato

Il nuovo tool MCP `assess_ubuntu_package` valuta il pacchetto
`apache2 2.4.29-1ubuntu4.21` su Ubuntu 18.04 Bionic, utilizzando snapshot
dei record CVE pubblicati da Ubuntu e l'ordinamento delle versioni Debian.
Il probe reale definitivo restituisce `status=assessed` con 120 CVE distinte:

| Esito | CVE | Significato |
|---|---:|---|
| `fixed` | 34 | La versione inventariata raggiunge il fix Ubuntu |
| `not_affected` | 28 | Ubuntu esclude il pacchetto/release; eventuale soglia di versione verificata |
| `potentially_affected` | 46 | Versione inferiore al fix oppure problema aperto per la release |
| `unknown` | 12 | Nessuno stato `apache2`/`bionic` nel record acquisito |

Questi esiti riguardano **l'inventario**, non confermano vulnerabilità
sfruttabili nel processo osservato. Restano `runtime_applicability=not_assessed`
e `historical_runtime_state=not_established`. La valutazione è isolata e
non è ancora collegata alla Workforce.

## Evidenza e ambito temporale

Il [resolver CTI v2](cti-identity-resolution-v2.md) continua a restituire
sei identità equivalenti fra 113 candidate. Le loro 129 entry CNA/ADP
corrispondono a 120 CVE uniche: il servizio valuta ciascuna una sola volta,
conservando tutte le identità che vi rimandano.

Il servizio legge una copia verificata dei facts originali: `apache2` e
`apache2-bin` risultano entrambi installati alla revisione `2.4.29-1ubuntu4.21`,
architettura `amd64`, origine Ubuntu e gestore apt. L'associazione al source
package `apache2` è controllata anche nei metadati dei pacchetti binari
dell'[avviso Ubuntu USN-5212-1](https://lists.ubuntu.com/archives/ubuntu-security-announce/2022-January/006337.html).

L'inventario è del **25 gennaio 2022**. I messaggi Apache sono del 22–24
gennaio: i facts successivi non attestano quale revisione stesse eseguendo
il processo in ciascun messaggio, né l'avvenuto riavvio dopo un aggiornamento.
Lo snapshot OTel originale rimane invariato.

La conoscenza del tracker Ubuntu è quella dello snapshot acquisito e viene applicata
retrospettivamente alla versione inventariata. Non si ricostruisce la CTI
disponibile al momento degli eventi. Le date `published` e `updated_at`
dei record restano nell'output come dati della fonte.

## Regole della valutazione

Per ogni CVE sono selezionati esclusivamente il source package `apache2` e
la release `bionic`. Il risultato conserva URL e hash del record, puntatori
alle righe di stato, pocket, descrizione dello stato e confronto effettuato.

- `released`, con versione Debian valida: confronto della revisione completa;
  se l'inventario raggiunge la soglia, `fixed`, altrimenti `potentially_affected`.
- `not-affected`: `not_affected`; se la descrizione contiene una soglia di
  versione e l'inventario la precede, il risultato resta `unknown`.
- `needed`, `pending`, `deferred`: `potentially_affected`.
- Stato mancante, multiplo, non interpretabile, record indisponibile o
  ritirato: `unknown`. `ignored` non viene convertito in assenza di vulnerabilità.

Il confronto usa `python-debian==1.0.1`, classe `debian.debian_support.Version`:
gestisce epoch, revisioni, suffissi `~` ed ESM secondo
la [policy Debian sulle versioni](https://www.debian.org/doc/debian-policy/ch-controlfields.html#version).
Un controllo sintattico impedisce di interpretare note come `windows-specific`
o `pending-release` come versioni. Non vengono usati confronti lessicografici
o SemVer sulla sola parte `2.4.29`.

La soglia del fix non descrive necessariamente la versione in cui un difetto
è stato introdotto. Perciò una revisione precedente al fix resta solo
potenzialmente applicabile. Moduli caricati, configurazione, piattaforme
specifiche, esposizione e condizioni di sfruttamento richiedono evidenze proprie.
Il risultato non aggiunge finding confermati alla Workforce.

## Esempi verificati

| CVE | Esito dell'inventario | Evidenza Ubuntu |
|---|---|---|
| `CVE-2021-44224` | `fixed` | Fix in `2.4.29-1ubuntu4.21`, uguaglianza |
| `CVE-2021-44790` | `fixed` | Fix in `2.4.29-1ubuntu4.21`, uguaglianza |
| `CVE-2021-41773` | `not_affected` | Stato Bionic esplicito |
| `CVE-2024-38472` | `not_affected` | Stato Bionic esplicito, problema Windows |
| `CVE-2022-22720` | `potentially_affected` | Fix in `2.4.29-1ubuntu4.22`, inventario precedente |
| `CVE-2019-17567` | `potentially_affected` | Stato Bionic `deferred` |

I due fix della revisione `.21` sono attestati anche dal
[changelog dell'archivio Ubuntu](https://lists.ubuntu.com/archives/bionic-changes/2022-January/037000.html).
La soglia `.22` per `CVE-2022-22720` è riportata in
[USN-5333-1](https://ubuntu.com/security/notices/USN-5333-1), mentre
[Ubuntu esclude esplicitamente Bionic per CVE-2024-38472](https://ubuntu.com/security/CVE-2024-38472).

Le 12 CVE indeterminate sono `CVE-2016-0736`, `CVE-2016-2161`,
`CVE-2016-8740`, `CVE-2016-8743`, `CVE-2017-3167`, `CVE-2017-3169`,
`CVE-2017-7659`, `CVE-2017-7668`, `CVE-2017-7679`, `CVE-2017-9788`,
`CVE-2017-9789` e `CVE-2017-9798`. I record sono presenti, ma non riportano
uno stato Bionic. Non sono errori di download e non sono esclusioni implicite.

## Contratto e separazione dei servizi

Il [contratto pubblico](../thesis_agents/mcp/ubuntu_contracts.py) è
`ubuntu-package-assessment-v1`. Il client invia l'evidenza già usata dal
resolver, distribuzione, release e versione della distribuzione. Il server:

1. verifica integrità del manifest e di tutti i file dello snapshot;
2. risolve nuovamente l'identità tramite il servizio v2;
3. controlla hash, tempo e versione dell'inventario contro i facts conservati;
4. controlla che gli snapshot Ubuntu siano preparati per la stessa revisione
   del dataset e della regola d'identità;
5. produce un risultato per ogni CVE selezionata, oppure `not_assessed`
   se identità, inventario o ambito delle fonti non coincidono.

La risposta incorpora il risultato d'identità originale e una valutazione
Ubuntu separata. Il suo `package_applicability=not_assessed` rimane quello
del contratto d'identità: i nuovi esiti sono in `PackageAssessment.results`.
Il client controlla richiesta, tipo del backend, hash del dataset e manifest
attesi, corrispondenza dei facts, completezza delle CVE e conteggi.

Il processo degli agenti non importa il motore CTI, il comparatore Debian
o i file delle fonti. La nuova dipendenza è del solo servizio esterno,
documentata in `app/src/cti_mcp/requirements-ubuntu.txt`. Gli algoritmi,
i contratti preesistenti e i resolver v1/v2 non vengono modificati.

Hash e URL rendono controllabili gli snapshot forniti all'operatore; non
costituiscono attestazione remota dell'esecuzione o dell'autenticità dei facts.
Lo snapshot locale fissa dati acquisiti da più richieste HTTP, non una
transazione atomica del tracker Ubuntu.

## Riproduzione e artefatti

Sono disponibili 120 record JSON dall'
[API pubblica Ubuntu](https://ubuntu.com/security/api/docs), il notice di
packaging e i facts nella directory locale `output/ubuntu-apache-sources/`.
Il manifest è immutabile e riporta il tempo di preparazione del bundle,
distinto dall'ora storica dell'inventario. Questi output non sono inclusi nel clone Git.

La preparazione offline, dalla radice del backend, riusa le acquisizioni
con URL e hash già conservati, rifiutando una directory di destinazione esistente:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=app/src \
  /Users/reucalion/tesi/.venv/bin/python -m cti_mcp.ubuntu_sources \
  --identity-resolution /Users/reucalion/tesi/output/apache-identity-resolution-r3/identity_resolution.json \
  --facts /Users/reucalion/tesi/output/baseline-apache-metadata/members/gather/webserver/facts.json \
  --cve-manifest /Users/reucalion/tesi/output/ubuntu-applicability-development/cve-source-manifest.json \
  --support-manifest /Users/reucalion/tesi/output/ubuntu-applicability-development/initial-source-manifest.json \
  --output-dir /Users/reucalion/tesi/output/ubuntu-apache-sources
```

Un clone nuovo deve prima acquisire i record dagli URL del manifest o
preparare una nuova acquisizione. Un record dichiarato indisponibile nel
manifest produce `unknown`; un file dichiarato presente ma assente o alterato
causa errore. Per avviare il servizio, dopo aver installato la dipendenza:

```sh
/Users/reucalion/tesi/.venv/bin/python -m pip install \
  -r app/src/cti_mcp/requirements-ubuntu.txt
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=app/src \
  /Users/reucalion/tesi/.venv/bin/python -m cti_mcp.ubuntu_server \
  --sqlite app/data/cve2owl_20260523_143950.affected.sqlite \
  --dataset-id cve2owl_20260523_143950 --dataset-kind real \
  --sources /Users/reucalion/tesi/output/ubuntu-apache-sources/manifest.json --port 8006
```

Da `tesi`, scegliendo una directory nuova:

```sh
.venv/bin/python -m thesis_agents.mcp.ubuntu_probe \
  --url http://127.0.0.1:8006/mcp \
  --snapshot output/apache-recorded-integration/artifacts/telemetry_snapshot.json \
  --output-dir output/ubuntu-apache-applicability-r2 --expected-kind real \
  --dataset-sha256 e3566009408385c7aea7901a9e6499132f0ae4bb07ccbd80d22e2171e5f7990c \
  --sources-sha256 6e11b205b3e465d1afe5ac5757679af0f612a31530c060f148732d50a289af62
```

Il [riepilogo definitivo](../output/ubuntu-apache-applicability-r2/summary.json),
la [risposta per CVE](../output/ubuntu-apache-applicability-r2/package_assessment.json)
e la [verifica di conservazione](../output/ubuntu-apache-applicability-r2/verification.json)
conservano il collaudo MCP. Snapshot e risultato d'identità coincidono con
quelli precedenti. Il probe salva richiesta, audit e riepilogo anche in caso
di errore, senza pubblicare una valutazione di dominio fallita.

La prima prova in `output/ubuntu-apache-applicability/` è preservata come
storico: aveva tre ulteriori esiti `unknown` perché `windows-specific` era
interpretato dal comparatore come versione legacy. Il vincolo sintattico
e tre regressioni correggono quei casi. La seconda prova usa gli stessi
snapshot e classifica quei tre record come `not_affected`.

Le verifiche finali passano: **320 test del prototipo**, **69 test MCP del
backend**, Ruff, formato dei file aggiunti e `git diff --check`.
`pip check` non segnala dipendenze incompatibili. Contratti client/server
sincronizzati, componenti preesistenti preservati e servizio temporaneo
sulla porta 8006 arrestato dopo il probe.

Nel successivo incremento il [collegamento al VulnerabilityAgent](ubuntu-vulnerability-agent.md)
è stato completato e collaudato nella Workforce con servizi reali e inferenza
programmata. La valutazione del pacchetto mantiene distinti i finding runtime
e preserva i 12 casi indeterminati. Il probe isolato documentato qui rimane
conservato come verifica precedente.
