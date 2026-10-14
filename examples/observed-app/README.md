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

`--skip-build` riusa gli artefatti Maven presenti, ma crea sempre una nuova
esecuzione dell'applicazione. Non usarlo dopo modifiche alla build.

Lo script prepara le fonti: non avvia CAMEL, gateway o LLM. La raccolta usa
log SDK su file (`sdk-file`), senza Collector, tracce o metriche. Il confronto
del JAR è un controllo locale di coerenza, non un'attestazione remota.

Comandi per avviare i tre servizi, collaudo CAMEL, diagramma, risultati,
limiti e fonti sono nella
[guida dei tre ingressi](../../docs/observed-app-integration.md).
