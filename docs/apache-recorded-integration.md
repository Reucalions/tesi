# Ingresso Apache dai log registrati della baseline

Il gateway OTel supporta ora i tre messaggi di avvio Apache già
[ricondotti ai file originali AIT](baseline-apache-verification.md).
L'estensione è attivata esplicitamente con `--apache-binding`; i percorsi
statici, i self-log del Collector e gli attributi dell'applicazione Java
mantengono il comportamento precedente.

Il collaudo completo con i quattro agenti CAMEL, gateway HTTP e CTI reale
via MCP termina con `insufficient_evidence`, strategia `null`. Il nome
letterale `Apache` produce `no_match`: l'ingresso funziona, ma la risoluzione
CTI non è stata modificata per ottenere artificialmente finding.

## Dati e confini

```text
Export OTel della baseline + log originali AIT + facts dell'host
                 ↓ lettura esclusivamente lato servizio
Gateway HTTP: hash, confronto esatto del messaggio, estrazione della versione
                 ↓ snapshot validato
TelemetryAgent → RuntimeEvidence con recorded_context
                 ↓
VulnerabilityAgent → servizio CTI via MCP → VulnerabilityReport
                 ↓
CountermeasureAgent → CandidateStrategies
                 ↓
StrategicAgent legge separatamente tutti e tre gli artefatti
```

Il gateway riconosce soltanto il messaggio strutturato `AH00163` di avvio
`mpm_prefork` con `Apache/<versione> (Ubuntu)`. Richiede una corrispondenza
esatta e univoca fra il body OTel e una riga dei log originali configurati.
Non usa estrazione LLM, non interpreta righe YAML, non associa immagini Docker
a processi e non sostituisce eventuali attributi di risorsa già presenti.

La risposta mantiene tre livelli distinti:

| Livello | Dati | Origine |
|---|---|---|
| Osservazione runtime | `Apache`, `2.4.29`, ora nel messaggio | Body del record OTel e riga originale |
| Attribuzione della sorgente | Host `webserver`, servizio `apache2`, FQDN | Percorso originale e facts |
| Inventario | `apache2 2.4.29-1ubuntu4.21`, Ubuntu 18.04, tempo dei facts | `/packages/apache2/0` e campi dei facts |

Il campo di selezione `service_instance_id` contiene in questo profilo
`dataset:russellmitchell:webserver:apache2`: è un'etichetta di ambito definita
dall'adattatore, **non un identificatore di istanza runtime osservato**.
`recorded_context.instance_basis` lo dichiara esplicitamente. La finestra
dell'input seleziona il tempo di osservazione del Collector; il testo dell'ora
storica dell'evento rimane in `original_log.event_time_text`, senza inventare
un fuso orario. L'acquisizione è esclusivamente `recorded`.

`recorded_context` è un campo opzionale dello snapshot e del riferimento
telemetrico in `RuntimeEvidence`. Contiene soltanto la proiezione necessaria
dei facts, i riferimenti e gli hash; il file integrale dei facts resta nel
servizio. I riferimenti alle singole righe originali rimangono nello snapshot.
L'LLM non deve ricostruire o correggere questi metadati: la pubblicazione
deve coincidere con l'evidenza acquisita, come già previsto da `ArtifactSession`.
La spiegazione finale include la distinzione fra versione runtime e inventario.

Questa è un'estensione opzionale del contratto nel repository: server e client
devono usare gli schemi aggiornati. Non è stata attestata la compatibilità
del nuovo payload con client esterni che rifiutano campi non conosciuti.

## Preparazione e avvio

I membri originali recuperati sono in
`output/baseline-apache-metadata/members/`; l'export della baseline resta nel
repository esterno. I file in `output/` non fanno parte del clone Git e devono
essere disponibili prima di riprodurre la prova. La preparazione non scarica
file: identifica con hash quelli forniti dall'operatore. La corrispondenza
con il dataset pubblico è documentata nella verifica preliminare, non attestata
dal solo hash o dal nome del file.

Dalla radice di `tesi`, creare una configurazione nuova senza sovrascriverne
una esistente:

```sh
.venv/bin/python -m services.otel_gateway.apache_recorded \
  --export /Users/reucalion/Desktop/agent-based-cti-argumentation-pipeline/opentelemetry/data/otel-zenodo-logs.json \
  --members output/baseline-apache-metadata/members \
  --output output/baseline-apache-metadata/gateway-binding.json
```

Il binding contiene percorsi locali al server e hash di export, facts e log.
Il gateway ricontrolla i file a ogni acquisizione; nessun percorso locale
assoluto viene inviato al MAS. Un file alterato, una corrispondenza assente
o duplicata e un tentativo di presentare il caso come live causano un errore.

```sh
.venv/bin/python services/otel_gateway/server.py \
  --file /Users/reucalion/Desktop/agent-based-cti-argumentation-pipeline/opentelemetry/data/otel-zenodo-logs.json \
  --source-id ait-russellmitchell-apache --acquisition recorded \
  --apache-binding output/baseline-apache-metadata/gateway-binding.json --port 8004
```

Avviare il servizio CTI esistente come descritto nella
[verifica Apache](baseline-apache-verification.md#riproduzione-e-artefatti).
Il profilo [backends.otel-apache-cti.json](../config/backends.otel-apache-cti.json)
usa telemetria HTTP, lookup MCP reale e tool strategici mock locali.
L'arricchimento SBOM/OSV è disabilitato: non viene riutilizzata una SBOM Maven
estranea al servizio Apache. I facts sono un inventario storico, non una SBOM
di build. L'input non dichiara capacità operative non documentate.

Per il collaudo senza inferenza LLM, con directory di output nuova:

```sh
.venv/bin/python tests/support/otel_workforce_smoke.py \
  --input config/input.otel-apache-recorded.json \
  --backends config/backends.otel-apache-cti.json \
  --output-dir output/apache-recorded-integration
```

## Risultato verificato

La [prova salvata](../output/apache-recorded-integration/summary.json) ha:

- letto 1.109 record, riconosciuto e selezionato i tre avvii Apache;
- conservato la versione runtime `2.4.29` e quella inventariale
  `2.4.29-1ubuntu4.21` in campi diversi;
- interrogato il backend CTI reale con `Apache`, versione `2.4.29`;
- pubblicato `lookup_status=no_match`, candidate vuote e decisione
  `insufficient_evidence`, senza strategia selezionata;
- completato tutti gli artefatti e la provenienza mock, superando
  `ArtifactSession.assert_complete()`;
- verificato che i tre artefatti distinti arrivino nello
  [stesso contesto letto dallo Strategic](../output/apache-recorded-integration/strategic_context.json).

Il modello è `ScriptedToolModel`, esclusivamente di test. Il collaudo usa
CAMEL e i trasporti effettivi, ma non misura ragionamento o affidabilità di
Ollama. Il modello di test non gestisce la valutazione qualitativa gestionale
dell'SDK: CAMEL registra avvisi e usa il proprio fallback per quella fase.
Non vanno interpretati come valutazioni qualitative prodotte da un LLM.

I test automatici usano fixture sintetiche dichiarate e non richiedono il
dataset privato né download. Verificano separazione dei dati, file alterati,
identità di risorsa in conflitto, corrispondenze assenti/duplicate, contesto
obbligatorio per il nuovo tipo di osservazione, rifiuto di pubblicazioni
modificate e consegna allo Strategic attraverso HTTP e quattro agenti CAMEL.

Verifica dell'incremento di ingresso: `.venv/bin/python -m pytest -q` → **281 passed**;
`.venv/bin/ruff check .` e `git diff --check` superati. Il servizio CTI e il
gateway avviati per quel collaudo sono stati arrestati. In quell'incremento
il repository esterno è rimasto invariato.

## Incremento successivo: resolver CTI isolato

Il [resolver CTI Apache](cti-identity-resolution.md) introduce ora una
normalizzazione esplicita e tracciabile tramite il tool MCP
`resolve_software_identity`. Il secondo probe sul database reale conferma
`ambiguous`: tre identità equivalenti, sedici escluse e l'alias
`apache::http_server` irrisolto; le 20 candidate raggiungono il limite della
ricerca. Non vengono selezionati né un gruppo né identità, e l'applicabilità
al pacchetto Ubuntu resta `not_assessed`.

Il resolver è un'aggiunta separata nel backend ed è collaudato fuori dalla
Workforce. Il profilo e il risultato CAMEL descritti sopra continuano a usare
il lookup letterale. La guida del resolver conserva comandi, contratto,
evidenza del nuovo probe e differenze dalla risposta storica.

Il [successivo resolver v2](cti-identity-resolution-v2.md) completa la revisione
degli alias e supera i limiti della ricerca: r3 restituisce `resolved`, sei
identità equivalenti fra 113 candidate e copertura lessicale dichiarata sullo
snapshot. L'applicabilità Ubuntu resta `not_assessed` e il risultato Workforce
rimane quello del lookup letterale.

La [valutazione Ubuntu separata](ubuntu-package-applicability.md) considera
ora la revisione completa dell'inventario: 34 CVE corrette, 28 non applicabili
secondo Ubuntu, 46 potenzialmente applicabili e 12 indeterminate su 120 CVE.
La valutazione non attesta lo stato del processo nei log precedenti ai facts
e non modifica il profilo Workforce già collaudato.

## Lavoro escluso da questo aggiornamento

Il successivo [collegamento al VulnerabilityAgent](ubuntu-vulnerability-agent.md)
è completato con il profilo `backends.otel-apache-ubuntu.json`.
Restano l'approfondimento dei casi indeterminati e la verifica delle condizioni runtime.
Il campo completo del pacchetto non viene passato automaticamente al
valutatore upstream. Non sono state applicate mitigazioni o realizzati nuovi
smart contract, ledger o PROV-O.
