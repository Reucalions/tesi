# Applicazione osservata per il collaudo degli ingressi

Piccolo workload Java locale: usa Log4j, emette cinque log tramite l'SDK
OpenTelemetry e termina. Maven genera la SBOM CycloneDX delle dipendenze della
build. Serve a fornire alla Workforce telemetria e inventario dello stesso
software, verificandone versione e SHA-256 del JAR.

Dalla radice di `tesi`, con Java 17+ e Maven disponibili:

```sh
.venv/bin/python examples/observed-app/prepare.py \
  --output output/observed-app-sources-03
```

Il progetto Python deve essere installato nell'ambiente. La directory di
output deve essere nuova. Il comando esegue la build, avvia Java, verifica le
fonti e salva `otel.jsonl`, `sbom.cdx.json`, `source_manifest.json`, `input.json`,
`binding.json`, `backends.json`, POM, JAR applicativo e log. Le dipendenze Java
sono scaricate nella cache Maven; `target/` è escluso da Git.

Per i casi controllati successivi all'audit KG del 6 novembre e disponibile
anche il profilo Logback. Lo stesso workload usa la dipendenza caricata e
verifica l'identita Maven direttamente dal suo JAR:

```sh
.venv/bin/python examples/observed-app/prepare.py \
  --component logback-core --dependency-version 1.5.24 \
  --output output/logback-sources-vulnerable
```

Il controllo negativo usa `--dependency-version 1.5.25`. La versione richiesta
e soltanto un parametro di build: viene confrontata con quella realmente caricata.
`thesis.software.name` conserva l'artifactId letto da pom.properties; il titolo
Implementation-Title del manifest resta in `thesis.software.manifest.title`.
Non e applicata una correzione nascosta dell'identita CTI. Il profilo predefinito
Log4j resta disponibile. Per i due collaudi del 6 novembre sono state usate copie
isolate del progetto, preservando anche i sorgenti e i fallimenti precedenti.

`--skip-build` riusa gli artefatti Maven presenti, ma crea sempre una nuova
esecuzione dell'applicazione. Non usarlo dopo modifiche alla build.

Lo script prepara le fonti: non avvia CAMEL, gateway o LLM. La raccolta usa
log SDK su file (`sdk-file`), senza Collector, tracce o metriche. Il confronto
del JAR è un controllo locale di coerenza, non un'attestazione remota.

Comandi per avviare i tre servizi, collaudo CAMEL, diagramma, risultati,
limiti e fonti sono nella
[guida dei tre ingressi](../../docs/integrazioni/observed-app-integration.md).
