# Verifica preliminare del caso Apache nella baseline OTel

La prova rilegge i log registrati della baseline e interroga nuovamente il
backend CTI attraverso MCP, senza LLM, Workforce o modifiche al gateway.
Entrambe le risposte superano discovery e validazione del contratto, ma
**nessuna delle due richieste produce finding pubblicabili con il mapping
attuale**. Un collegamento riuscito non implica un'identità risolta.

La successiva verifica dei metadati, descritta in fondo al documento, ha
ricondotto tutti e tre i messaggi ai log originali dell'host `webserver` e
recuperato la versione del pacchetto Ubuntu. Questo risolve l'attribuzione
alla sorgente, ma non modifica gli esiti CTI riportati qui.
Il successivo [adattamento dell'ingresso](apache-recorded-integration.md)
implementa il binding nel gateway e ne verifica il percorso fino allo Strategic;
le sezioni seguenti conservano gli esiti della ricognizione preliminare.

## Fonte e osservazioni

Repository locale: `agent-based-cti-argumentation-pipeline`, branch
`costa-thesis`, commit `3b483624286262f2e0ac94b4b950b904a5dc2ad4`.
File: `opentelemetry/data/otel-zenodo-logs.json`.
SHA-256: `bf968227f01304afb937da542d84a829be93e72249f023a71053cd7a414a30a3`.

Sono presenti tre messaggi `AH00163` di avvio del modulo `mpm_prefork`, con
`Apache/2.4.29 (Ubuntu) OpenSSL/1.1.1 configured -- resuming normal operations`.
I record si trovano nella prima riga NDJSON, ai puntatori
`/resourceLogs/0/scopeLogs/0/logRecords/1`, `/3` e `/6` (gli ultimi due
condividono lo stesso prefisso). La prova utilizza il primo record.

Il manifest conserva i record integrali, i timestamp originali, la risorsa
vuota e un identificativo derivato dall'hash del file e dalla posizione del
record. Non viene prodotto un nuovo `RuntimeEvidence`: il contratto attuale
richiede anche identificazione del servizio/istanza, assente da questi record.
Il tempo di osservazione del Collector e la data nel messaggio storico non
sono intercambiabili. La lettura odierna dell'export non è una raccolta live.

## Richieste e risultati

Il servizio esterno è quello esistente, avviato su loopback, con indice
`cve2owl_20260523_143950.affected.sqlite`, dataset dichiarato reale e hash
`e3566009408385c7aea7901a9e6499132f0ae4bb07ccbd80d22e2171e5f7990c`.
Il client non importa il motore della baseline né legge il database.
Il limite di matching resta 5; il vendor non viene specificato.

| Richiesta, versione 2.4.29 | Natura del nome | Esito del mapping | Finding pubblicati |
|---|---|---|---:|
| `Apache` | Nome letterale nel messaggio | `no_match` | 0 |
| `Apache HTTP Server` | Interpretazione esplicita del messaggio di avvio | `ambiguous` | 0 |

La seconda richiesta è diagnostica: non introduce un alias automatico nel
prototipo. Restituisce tre identità con confidenza `high`, distinte per vendor
(`Apache Software Foundation`, `n/a`, `Apache`), e due candidate `needs_review`
(`net/http`, `HTTP Server`). Non viene selezionata silenziosamente la prima.

Per l'identità `apache software foundation::apache http server`, il backend
classifica 43 entry CVE come `vulnerable`, 17 come `not_vulnerable` e 46 come
`not_evaluable`. Sono risultati grezzi del valutatore per quella candidata:
**non costituiscono 43 vulnerabilità confermate dell'applicazione osservata**.
La copertura delle regole è parziale e il mapping conservativo restituisce
`ambiguous`, con lista di finding vuota. Non è l'esito negativo `no_findings`.

Il log dichiara Ubuntu, ma non contiene la revisione del pacchetto né lo stato
delle patch della distribuzione. La valutazione sulla sola versione upstream
non accerta tali informazioni. Non sono stati interrogati OSV, eseguiti attacchi,
generate strategie o applicate mitigazioni.

## Riproduzione e artefatti

Dalla radice della baseline, con il database già disponibile:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=app/src \
  /Users/reucalion/tesi/.venv/bin/python -m cti_mcp.server \
  --sqlite app/data/cve2owl_20260523_143950.affected.sqlite \
  --dataset-id cve2owl_20260523_143950 --dataset-kind real --port 8003
```

Dalla radice di `tesi`, usando directory di output nuove a ogni prova:

```sh
.venv/bin/python -m thesis_agents.mcp.cti_probe \
  --url http://127.0.0.1:8003/mcp --expected-kind real \
  --product Apache --version 2.4.29 \
  --evidence-id '<ID dal manifest source-evidence.json>' \
  --output-dir output/apache-literal-repeat --timeout 60

.venv/bin/python -m thesis_agents.mcp.cti_probe \
  --url http://127.0.0.1:8003/mcp --expected-kind real \
  --product 'Apache HTTP Server' --version 2.4.29 \
  --evidence-id '<stesso ID dal manifest>' \
  --output-dir output/apache-interpreted-repeat --timeout 60
```

Il probe conserva richiesta, risposta, audit e hash. La prova documentata
applica inoltre `thesis_agents.tools.cti_mcp.map_assessment` per verificare
la traduzione nel contratto del prototipo, senza modificarne la logica.

Evidenze locali, in `output/` non versionato:

- [Manifest e record originali](../output/baseline-apache-verification/source-evidence.json).
- [Confronto dei due lookup](../output/baseline-apache-verification/comparison.json).
- [Risposta al nome interpretato](../output/baseline-apache-verification/interpreted-http-server/assessment.json).
- [Mapping conservativo](../output/baseline-apache-verification/interpreted-http-server/mapped-lookup.json).
- [Script della verifica](../output/baseline-apache-verification/verify.py).

Lo script verifica anche che il file sorgente non sia cambiato. Le directory
dei probe non possono essere sovrascritte. Nessun test LLM è stato eseguito e
il servizio temporaneo viene arrestato al termine della verifica.

## Conseguenze per l'integrazione

La baseline è riutilizzabile, ma questo caso non è ancora pronto come prova
end-to-end con finding. Prima di estendere il gateway occorre definire una
regola di identificazione tracciabile: nome osservato, eventuale normalizzazione,
identità CTI scelta e motivazione devono rimanere distinti. Aggiungere un vendor
alla richiesta solo per ottenere un match unico non risolve la carenza di prove.

Il passo successivo è verificare se i metadati del dataset permettono di
attribuire servizio, istanza e identità del pacchetto; in alternativa il caso
può collaudare esplicitamente il ramo di evidenza insufficiente. Il ramo con
finding richiede una fonte la cui identità sia risolvibile con criteri dichiarati.
L'integrazione SBOM/OSV resta separata: il supporto attuale per un componente
Maven non fornisce una SBOM dell'installazione Apache registrata.

## Verifica dei metadati originali

La ricognizione del repository e della cronologia locale non ha individuato
un DOI né i file originali del dataset. Il percorso configurato nel Collector
indica però `russellmitchell/gather/webserver`. La ricerca della fonte pubblica
ha individuato l'[AIT Log Data Set V2.0](https://zenodo.org/records/5789064),
DOI `10.5281/zenodo.5789064`, e il relativo archivio `russellmitchell.zip`.
La descrizione degli autori classifica i dati come log sintetici raccolti
in testbed con attività simulate: il caso va presentato come **scenario
sperimentale pubblicato**, non come incidente osservato in produzione.

Sono stati recuperati soltanto l'indice ZIP e sei file selezionati mediante
richieste HTTP Range: `dataset.yaml`, `gather/webserver/facts.json` e quattro
file `error.log.*`. Il trasferimento dell'archivio è di 2.392.190 byte,
contro 7.132.670.599 byte dell'archivio completo. Le risposte parziali sono
controllate per stato HTTP, intervallo e lunghezza; ciascun file estratto
supera il controllo CRC ZIP ed è identificato con SHA-256. Il checksum MD5
dell'intero archivio, pubblicato da Zenodo, non è stato verificato: l'archivio
completo non è stato scaricato. I file pubblici sono dati di consultazione;
nessuno script o configurazione contenuto nell'archivio è stato eseguito.

Il confronto dei messaggi, senza normalizzazione del testo, produce:

| Record nell'export OTel, prima riga NDJSON | File originale nell'archivio, riga 1 | Esito |
|---|---|---|
| `/resourceLogs/0/scopeLogs/0/logRecords/1` | `gather/webserver/logs/apache2/error.log.1` | Identico |
| `/resourceLogs/0/scopeLogs/0/logRecords/3` | `gather/webserver/logs/apache2/error.log.2` | Identico |
| `/resourceLogs/0/scopeLogs/0/logRecords/6` | `gather/webserver/logs/apache2/error.log.3` | Identico |

La corrispondenza conferma il contenuto e l'attribuzione all'host nel dataset
pubblicato. Non dimostra da quale versione dell'archivio sia stato effettuato
il download originario nella baseline, che non conserva quel manifest.

Nel file `gather/webserver/facts.json` sono presenti:

| Informazione | Valore | Puntatore JSON |
|---|---|---|
| Host nell'inventario | `webserver` | `/inventory_hostname` |
| FQDN | `proxy.smith.russellmitchell.com` | `/ansible_fqdn` |
| Distribuzione | Ubuntu 18.04, `bionic` | `/ansible_distribution`, `/ansible_distribution_version`, `/ansible_distribution_release` |
| Pacchetto | `apache2`, origine Ubuntu, gestore `apt` | `/packages/apache2/0` |
| Versione completa | `2.4.29-1ubuntu4.21` | `/packages/apache2/0/version` |
| Servizio nel rilevamento dei facts | `apache2`, stato `running` | `/services/apache2` |

Il file contiene informazioni coerenti anche per `apache2-bin`, `apache2-data`
e `apache2-utils`. Le copie del pacchetto e del servizio sotto `ansible_facts`
coincidono con quelle usate nella verifica. I facts hanno un proprio tempo di
raccolta, successivo agli eventi Apache selezionati: documentano uno snapshot
del testbed, non attestano lo stato del pacchetto a ogni istante precedente.

### Conseguenze e confini della verifica

L'identità **della sorgente osservata** è ora documentata: scenario
`russellmitchell`, host `webserver`, servizio `apache2`. Il nome host non è
però un identificatore univoco dell'istanza runtime. Un futuro adattatore deve
distinguere questi dati dai campi dichiarati direttamente da OTel, oggi assenti,
senza modificare retroattivamente l'export originale.

La versione runtime `2.4.29` e quella di pacchetto `2.4.29-1ubuntu4.21` devono
restare separate. La presenza della revisione Ubuntu rende insufficiente
trasferire automaticamente le valutazioni upstream alla distribuzione. Questa
verifica non ha consultato advisory Ubuntu né stabilito quali patch fossero
applicate. Il lookup CTI resta `ambiguous`: i metadati non autorizzano a
scegliere una delle identità del dataset semplicemente per ottenere finding.

I facts forniscono un inventario utilizzabile per una futura proiezione SBOM,
con origine dichiarata e hash. Non sono già una SBOM CycloneDX e non rientrano
nel contratto OSV attuale, limitato a un componente Maven. Il lavoro successivo
può quindi partire da fonti disponibili, definendo separatamente:

1. attribuzione dei record e mapping verso `RuntimeEvidence`;
2. risoluzione esplicita dell'identità CTI, con traccia delle alternative;
3. valutazione del pacchetto Ubuntu e della sua revisione;
4. eventuale proiezione dell'inventario, senza presentarla come SBOM di build.

Non sono stati modificati agenti, gateway, contratti o repository esterno;
non sono state ripetute inferenze LLM o interrogazioni CTI in questa fase.

### Evidenze e riproduzione della verifica

- [Metadati del record Zenodo](../output/baseline-apache-metadata/zenodo-record.json).
- [Manifest dei file recuperati](../output/baseline-apache-metadata/download-manifest.json).
- [Richieste parziali e relativi hash](../output/baseline-apache-metadata/range-requests.json).
- [Collegamento verificato tra export, log e facts](../output/baseline-apache-metadata/source-binding.json).
- [Script di recupero selettivo](../output/baseline-apache-metadata/read_archive.py).
- [Verifica offline degli hash e dei collegamenti](../output/baseline-apache-metadata/verify_binding.py).

I file sono sotto `output/`, escluso dal versionamento. Dopo il recupero,
il controllo può essere ripetuto senza rete:

```sh
.venv/bin/python output/baseline-apache-metadata/verify_binding.py
```

Riferimento diretto per la fonte: Max Landauer, Florian Skopik, Maximilian
Frank, Wolfgang Hotwagner, Markus Wurzenberger e Andreas Rauber,
*AIT Log Data Set V2.0*, Zenodo, DOI
[10.5281/zenodo.5789064](https://doi.org/10.5281/zenodo.5789064).
La scheda indica come pubblicazione descrittiva *Maintainable Log Datasets for
Evaluation of Intrusion Detection Systems*, DOI
[10.1109/TDSC.2022.3201582](https://doi.org/10.1109/TDSC.2022.3201582).
In questa fase sono stati consultati la scheda e i file del dataset, non il
testo integrale dell'articolo.
