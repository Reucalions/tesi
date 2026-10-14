# Risposte cve2owl per regressione

Gli otto JSON sono risposte catturate dal servizio MCP locale sul dataset
`cve2owl_20260523_143950`, SHA-256
`e3566009408385c7aea7901a9e6499132f0ae4bb07ccbd80d22e2171e5f7990c`.
Non contengono il database né il codice del motore.

- I primi sette provengono da
  `output/cti-real-smoke-20261005T101110Z-f74ed28d/<caso>/assessment.json`.
- `core-negative.json` proviene da
  `output/cti-core-negative-20261006/assessment.json`, con prodotto osservato
  `Apache Log4j Core`, versione `2.25.4`, senza vendor.

La fonte implementativa è il servizio aggiuntivo `app/src/cti_mcp` del repository
privato `agent-based-cti-argumentation-pipeline`, branch `costa-thesis`.
Ogni risposta conserva gli hash dichiarati del motore e i riferimenti alle righe
del dataset. Il test controlla la trasformazione dei dati; non certifica le CVE.

`tests/support/cti_http_server.py` usa queste catture come **fixture**: adatta
l'eco della richiesta e restituisce `backend_kind=mock`, dataset `fixture` e
identificatori sintetici. I test HTTP non sono prove contro il dataset reale.
Le mutazioni negli unit test servono a verificare rifiuti e copertura parziale.
