# Gateway di consultazione degli export OTel

Servizio HTTP separato di sola lettura sugli export NDJSON del Collector della
baseline o dell'applicazione strumentata con SDK. Il processo degli agenti usa soltanto il contratto
`otel-observations-v1`; non legge il file e non importa il parser del gateway.

Dalla radice di `tesi`, nell'ambiente Python del progetto:

```sh
.venv/bin/python services/otel_gateway/server.py \
  --file /percorso/export-otel.json \
  --source-id sorgente-demo --acquisition recorded --port 8004
```

- `GET /health`: identificazione del backend.
- `POST /v1/observations`: `TelemetryQuery` JSON → `TelemetrySnapshot` JSON.
- Bind su `127.0.0.1`; server per collaudo locale, senza autenticazione integrata.
- Contratti: [telemetry_source.py](../../thesis_agents/schemas/telemetry_source.py).

È una API di consultazione applicativa, non un endpoint di ingestione OTLP.
Non avvia Collector, container o LLM. `recorded` indica un export conservato;
`collector-file` è una configurazione disponibile, non una garanzia di freschezza.
`sdk-file` identifica l'export diretto dell'SDK, collaudato con
[l'applicazione locale](../../docs/observed-app-integration.md); anche in questo
caso la freschezza va verificata dai timestamp.

Fonti, limiti del parser, comandi dei profili e risultati sono nella
[guida dell'integrazione](../../docs/opentelemetry-integration.md).
