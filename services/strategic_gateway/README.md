# Strategic evidence gateway

Servizio MCP HTTP separato per il ramo strategico senza candidate:
astensione esplicita dal ranking e archivio PROV-O JSON-LD su file.
Non esegue BWAF, Tiny-ME o transazioni Fabric. Un grafo non vuoto è rifiutato.

Dalla radice del repository:

```sh
.venv/bin/python -m services.strategic_gateway.server \
  --data-dir output/strategic-provenance-store --port 8007
```

Endpoint: `http://127.0.0.1:8007/mcp`.
Tool: `rank_graph`, `record_provenance`, `read_provenance`.
La directory di archivio contiene una sottodirectory immutabile per run,
con `record.json` e `provenance.jsonld`. La ricevuta distingue archivio su
file e ledger non utilizzato. Il client verifica la persistenza tramite
rilettura MCP, senza accesso ai percorsi locali del servizio.

Profilo: `config/backends.otel-apache-strategic.json`.
[Contratti, collaudo e limiti](../../docs/integrazioni/apache-strategic-agent.md).

È disponibile un secondo servizio, `fabric_server.py`, per i contratti nativi
via Fablo: grafo, ranking, Tiny-ME e chaincode PROV-O dedicato. Non sostituisce
il servizio di astensione e non converte implicitamente i grafi del MVP.
Configurazione, probe e stato del collaudo:
[integrazione Fabric](../../docs/archivio/fabric-native-integration.md).
