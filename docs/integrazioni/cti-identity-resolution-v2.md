# Resolver Apache v2: alias revisionati e copertura della ricerca

Il probe MCP reale v2 conclude con **`resolved`**, gruppo `apache:http_server`
e sei identità equivalenti. Conserva tutte le 113 candidate restituite dalla
ricerca lessicale: sei equivalenti, 107 escluse, nessuna irrisolta.
`package_applicability` resta **`not_assessed`**: questo esito d'identità non
conferma vulnerabilità Ubuntu. Il successivo
[collegamento al VulnerabilityAgent](ubuntu-vulnerability-agent.md) usa la
valutazione Ubuntu separata e conserva questa distinzione.

L'incremento aggiunge un contratto e un endpoint v2 separati. Il
[resolver v1 e i suoi probe](../archivio/cti-identity-resolution.md) restano conservati:
il probe r2 termina correttamente con `ambiguous` secondo la regola precedente.
Gli algoritmi e i contratti preesistenti della baseline non sono stati modificati.

## Revisione delle identità

La ricerca estesa ha reso visibili altri due alias oltre a
`apache::http_server`. Per le nove entry complessive dei tre alias sono stati
confrontati i record pubblici del CVE Program con le righe del database:

- il contenitore CNA è pubblicato da Apache e identifica `Apache HTTP Server`;
- il percorso ADP conservato nel database identifica esattamente vendor,
  prodotto e CPE presenti nel record pubblico;
- le CVE compaiono anche nella
  [pagina degli advisory HTTP Server](https://httpd.apache.org/security/vulnerabilities_24.html).

Per esempio, [CVE-2024-38472](https://raw.githubusercontent.com/CVEProject/cvelistV5/main/cves/2024/38xxx/CVE-2024-38472.json)
contiene sia il prodotto CNA `Apache HTTP Server` sia la forma ADP
`apache_software_foundation` / `apache_http_server`. Quella CVE riguarda
Windows: la corrispondenza di identità non stabilisce l'applicabilità a Ubuntu.

| Identità equivalente | Entry | Confidence del matcher conservata |
|---|---:|---|
| `apache software foundation::apache http server` | 106 | `high` |
| `n a::apache http server` | 9 | `high` |
| `apache::apache http server` | 5 | `high` |
| `apache::http_server` | 6 | `needs_review` |
| `apache_software_foundation::apache_http_server` | 2 | `needs_review` |
| `apache::apache_http_server` | 1 | `needs_review` |

La regola curata v2 giustifica l'equivalenza dei tre alias a bassa confidence
mediante l'esame delle fonti. Non modifica confidence, punteggi o risultati
di valutazione del matcher. La policy upstream continua a valutare soltanto
i match `high`; il resolver non esegue una nuova valutazione delle versioni.
Le 129 entry delle identità equivalenti rimangono distinte, anche quando CNA
e ADP si riferiscono alla stessa CVE.

Sono stati esaminati anche i record CNA di tre prodotti distinti:

| Prodotto escluso dal gruppo HTTP Server | Fonte CNA |
|---|---|
| Apache Airflow Providers Http | [CVE-2025-69219](https://raw.githubusercontent.com/CVEProject/cvelistV5/main/cves/2025/69xxx/CVE-2025-69219.json) |
| Apache Camel Platform HTTP Main | [CVE-2026-40022](https://raw.githubusercontent.com/CVEProject/cvelistV5/main/cves/2026/40xxx/CVE-2026-40022.json) |
| Apache Felix HTTP Webconsole Plugin | [CVE-2025-27867](https://raw.githubusercontent.com/CVEProject/cvelistV5/main/cves/2025/27xxx/CVE-2025-27867.json) |

Queste esclusioni sono esplicite e vincolate alle entry esaminate. Il solo
vendor Apache non basta a stabilire appartenenza o esclusione dal gruppo.
Un'identità potenzialmente pertinente non presente nella regola resta
`unresolved`; una variazione delle entry di un'identità già esaminata ha
lo stesso effetto.

La regola `apache-recorded-identity-v2` vincola ogni identità revisionata a
vendor, prodotto, confidence ammessa, elenco CVE e SHA-256 delle entry con
ID del database, IRI, percorso JSON e CPE. Conserva URL e hash dei nuovi
snapshot pubblici, oltre al riferimento alla revisione precedente.
La [revisione delle nove entry](../../output/cti-identity-r3-development/alias-review.json)
e il [manifest delle fonti](../../output/cti-identity-r3-development/sources/manifest.json)
sono disponibili fra gli output locali.

## Copertura dichiarata e limiti

Il nuovo servizio conta le identità utilizzabili con
`SQLiteProductStore.iter_product_identities()`, quindi invoca il matcher
preesistente con un limite superiore a quel conteggio. Anche il limite
interno per token risulta superiore al numero di identità dell'indice.
La generazione rimane quella della baseline: corrispondenze esatte e,
quando previsto dal matcher, ricerca per token distintivi. Non viene
aggiunto un filtro vendor per ridurre le alternative.

| Passaggio nel probe reale | Conteggio |
|---|---:|
| Identità utilizzabili nell'indice | 81.988 |
| Limite finale del matcher | 81.989 |
| Limite interno per token | 409.945 |
| Candidate generate, dopo deduplicazione | 220 |
| Candidate eliminate dal matcher come `no_match` | 107 |
| Candidate restituite e conservate dal resolver | 113 |
| Fra le 113: equivalenti / escluse / irrisolte | 6 / 107 / 0 |

Le 107 candidate eliminate dalla policy del matcher e le 107 escluse dal
resolver sono insiemi distinti. La risposta conserva i conteggi della prima
fase e tutte le identità restituite dalla seconda.

`search.coverage.complete=true` significa che i limiti non troncano questa
ricerca lessicale sullo snapshot. Il campo `scope` vale
`baseline-normalized-product-exact-and-token`; la ricerca vettoriale è
disabilitata. Non è una garanzia di copertura semantica di ogni possibile
alias, delle vulnerabilità assenti dal dataset o di fonti CTI esterne.

La risposta mantiene separatamente `upstream_assessment`, il lookup v1
originale con limite 20. Per le candidate presenti in entrambe le ricerche,
il contratto verifica identità, punteggio, confidence ed entry originali.
La ricerca estesa può aggiungere l'evidenza `sqlite_token` a una candidata
già trovata per corrispondenza esatta. I CPE vengono letti anche per le
candidate sotto soglia, senza valutarne le versioni.

## Contratto e riproduzione

Il [contratto pubblico client](../../thesis_agents/mcp/identity_v2_contracts.py)
è `cti-identity-resolution-v2`. La richiesta resta compatibile con
`IdentityRequest` v1. La risposta aggiunge `search`, con snapshot, hash
del motore, matching completo e copertura, e l'hash del dataset revisionato.
Gli stati sono derivati da revisione, copertura e classificazioni:

- contesto non supportato: `insufficient_evidence`, nessuna ricerca;
- dataset non revisionato: `unreviewed`, nessuna identità classificata;
- copertura incompleta o candidate irrisolte: `ambiguous`, nessuna selezione;
- copertura completa e almeno un'equivalente: `resolved`;
- copertura completa senza equivalenti né irrisolte: `no_match`.

Il probe richiede la selezione esplicita `--contract v2`; il default resta
v1. La discovery MCP verifica lo schema corrispondente. Sono rifiutate
risposte con conteggi incoerenti, candidate mancanti, risultati upstream
alterati o affermazioni di applicabilità del pacchetto.

Nel repository esterno sono aggiunti `identity_search.py`,
`identity_v2_contracts.py`, `identity_v2_service.py`, `identity_v2_server.py`,
`apache_identity_rules_v2.json` e `test_identity_v2.py`. Nessun file del
servizio precedente è modificato. Per avviare il nuovo endpoint dalla sua radice:

```sh
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH=app/src \
  /Users/reucalion/tesi/.venv/bin/python -m cti_mcp.identity_v2_server \
  --sqlite app/data/cve2owl_20260523_143950.affected.sqlite \
  --dataset-id cve2owl_20260523_143950 --dataset-kind real --port 8005
```

Da `tesi`, con directory nuova e snapshot disponibile:

```sh
.venv/bin/python -m thesis_agents.mcp.identity_probe \
  --url http://127.0.0.1:8005/mcp --contract v2 \
  --snapshot output/apache-recorded-integration/artifacts/telemetry_snapshot.json \
  --output-dir output/apache-identity-resolution-r3 \
  --expected-kind real \
  --dataset-sha256 e3566009408385c7aea7901a9e6499132f0ae4bb07ccbd80d22e2171e5f7990c
```

I file sotto `output/` sono locali e non inclusi nel clone Git; le directory
esistenti non vengono sovrascritte. Il database rimane vincolato allo stesso
hash dei probe precedenti. Non sono stati aggiornati dataset o log OTel.

Il [riepilogo r3](../../output/apache-identity-resolution-r3/summary.json), la
[risposta completa](../../output/apache-identity-resolution-r3/identity_resolution.json)
e la [verifica di conservazione](../../output/apache-identity-resolution-r3/verification.json)
attestano il risultato osservato. Snapshot e richiesta coincidono byte per
byte con r2; `upstream_assessment` è identico. Hash della regola impiegata:

```text
f1edde46dd88ca305f3dc7974e6e1bb5c5e6869f6d71e9cc4367507a2d1d6402
```

## Collaudo e passo successivo

I nuovi test sintetici verificano un alias oltre il vecchio limite per token,
la conservazione della confidence, CPE modificati, alias non revisionati,
copertura incompleta, cambio di dataset e regole, contesto non supportato,
coerenza degli schemi v1/v2 e riepilogo del probe. Il probe reale attraversa
discovery e chiamata MCP HTTP; non usa LLM e non avvia la Workforce.

Esiti: **308 passed** nella suite completa del prototipo e **40 passed**
nella suite MCP del backend. Ruff, formato dei file modificati e
sincronizzazione dei contratti superati. Il servizio temporaneo sulla porta
8005 è stato arrestato dopo il probe.

Il successivo incremento di [valutazione Ubuntu](ubuntu-package-applicability.md)
è ora collaudato separatamente: 34 CVE corrette, 28 non applicabili secondo
Ubuntu, 46 potenzialmente applicabili e 12 indeterminate per l'inventario.
Il contratto d'identità v2 rimane invariato. Il successivo
[collegamento al VulnerabilityAgent](ubuntu-vulnerability-agent.md) è completato:
il nuovo profilo Apache conserva la distinzione fra identità risolta,
valutazione del pacchetto e finding runtime. Il vecchio profilo con lookup
letterale `no_match` rimane disponibile per confronto.
