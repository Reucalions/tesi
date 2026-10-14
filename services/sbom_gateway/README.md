# Gateway SBOM/OSV

Processo HTTP separato, di sola lettura: carica una SBOM all'avvio e interroga
OSV per il componente Maven associato all'asset. Non genera strategie.

```sh
.venv/bin/python services/sbom_gateway/server.py \
  --sbom services/sbom_gateway/data/log4j-demo.cdx.json \
  --source-id log4j-demo --sbom-kind demo \
  --service-name payment-api --runtime-package log4j-core \
  --component-ref log4j-core --port 8005
```

Eseguire dalla radice di `tesi` con il progetto installato. Il default interroga
l'API OSV reale. La SBOM inclusa è un inventario **dimostrativo scritto a mano**,
non il risultato di una scansione dell'applicazione o dei repository della tesi.
La [demo con applicazione osservata](../../docs/observed-app-integration.md)
fornisce invece una SBOM generata dalla build Maven, servita con
`--sbom-kind provided` e confrontata con il JAR caricato a runtime.

- `GET /health`: identifica backend e modalità OSV.
- `POST /v1/enrichment`: `SupplyChainQuery` → `SupplyChainSnapshot`.
- Supporto iniziale: CycloneDX JSON 1.5/1.6, un componente Maven al primo livello.
- Bind su loopback; autenticazione/deployment remoto non inclusi.
- `--osv-kind mock --osv-url http://127.0.0.1:PORT/query`: upstream di test esplicito.

Contratti in [supply_chain.py](../../thesis_agents/schemas/supply_chain.py).
Fonti, comandi per CTI reale, vincoli e risultati nella
[guida dell'integrazione](../../docs/sbom-osv-integration.md).
