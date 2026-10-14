# Primo collaudo MCP con il dataset cve2owl reale

Il servizio di lookup su `costa-thesis` comunica con il client di `tesi` su
`full` usando il database reale. Il collaudo del 5 ottobre 2026 comprende sette
richieste HTTP in processi separati, tutte concluse con risposte valide.
Non è un'esecuzione della Workforce: non sono stati usati LLM, Weaviate,
smart contract o ledger.

## File e provenienza

Il file fornito in Downloads con estensione `.affected.sqlite` era un puntatore
Git LFS di 134 byte. Coincide con quello in
`main:app/data/cve2owl_20260523_143950.affected.sqlite` della copia locale di
`sisinflab-swot/agent-based-cti-argumentation-pipeline`, commit
`9b68780fcfcf3661807f6cbae1ae59297dabce75`.

È stato recuperato l'oggetto effettivo tramite la
[Git LFS Batch API](https://github.com/git-lfs/git-lfs/blob/main/docs/api/batch.md),
con l'accesso GitHub già configurato. Dimensione e SHA-256 coincidono con il
puntatore. Il database è ora in:

```text
/Users/reucalion/Desktop/agent-based-cti-argumentation-pipeline/app/data/cve2owl_20260523_143950.affected.sqlite
```

Non sono stati cambiati branch, sorgenti o configurazioni del backend.
L'indice è ignorato da Git sul branch `costa-thesis`.
Il puntatore originale in Downloads è stato conservato.

| File | Dimensione in byte | SHA-256 |
|---|---:|---|
| Indice SQLite effettivo | 397623296 | `e3566009408385c7aea7901a9e6499132f0ae4bb07ccbd80d22e2171e5f7990c` |
| File OWL ricevuto | 5062301486 | `0ffa87d0ff610cd7860dc3cae4bd84e65ab223569ba19ef2f4240fba6da59350` |

L'OWL rimane in `/Users/reucalion/Downloads/cve2owl_20260523_143950.owl`, senza
duplicarne i circa 5 GB. Sono stati calcolati il digest e controllate alcune
asserzioni di versione in sintassi OWL Functional. Non è stata eseguita una
validazione sintattica/semantica completa dell'ontologia. Il servizio consulta
solo SQLite; non esegue un reasoner sul file OWL.

L'identificativo `cve2owl_20260523_143950` deriva dal nome dei file. Non certifica
data di aggiornamento delle fonti, copertura o versione del generatore.
Gli hash identificano esattamente i file usati; informazioni sulla generazione
e riferimenti bibliografici restano da acquisire dall'autore.

## Verifiche sui dati

SQLite è stato aperto in sola lettura. `PRAGMA integrity_check` ha restituito
`ok`; l'avvio del servizio ha verificato le colonne necessarie al matcher e al
valutatore. Il digest del database è rimasto invariato al termine delle prove.

| Tabella | Righe |
|---|---:|
| `cve_record` | 352234 |
| `affected_product` | 584678 |
| `affected_version` | 1134883 |
| `affected_version_change` | 12503 |
| `affected_cpe` | 169791 |

I record CVE comprendono 334685 `PUBLISHED` e 17549 `REJECTED`: il totale non
va presentato come numero di vulnerabilità pubblicate attive. L'integrità
SQLite verifica la struttura del database, non la correttezza dei dati CTI.

## Risultati

Backend eseguito al commit `3b48362` di `costa-thesis`, con matching SQLite
esatto/per token, massimo cinque candidati e valutazione limitata alla
confidenza `high`. Il client ha verificato schemi, riferimenti alle evidenze,
hash delle richieste e coerenza di matching/assessment.

| Richiesta | Risultato osservato |
|---|---|
| `log4j-core`, `2.14.1`, senza vendor | `needs_review`: cinque candidati; nessuno valutato con la policy attuale |
| `Apache Log4j2`, vendor `Apache Software Foundation`, `2.14.1` | Identità trovata; `CVE-2021-44228`: `not_evaluable` |
| `Apache Log4j`, stesso vendor, `1.2.17` | `CVE-2023-26464`: `vulnerable` |
| `Apache Log4j`, stesso vendor, `2.0` | `CVE-2023-26464`: `not_vulnerable` |
| `Apache Log4j2`, stesso vendor, versione `unknown` | `CVE-2021-44228`: `not_evaluable` |
| `zzzzcostathesisabsent9f832c`, `1.0` | `no_match`, nessuna valutazione |
| `Apache Log4j Core`, stesso vendor, `2.14.1` | `CVE-2025-68161`: `vulnerable` |

Gli esiti delle CVE si riferiscono ai record e alle regole di questo snapshot,
non a una valutazione indipendente aggiornata dei prodotti. In particolare,
`not_vulnerable` nella quarta riga non significa che la versione sia priva
di altre vulnerabilità.

L'intera prova ha richiesto circa 3,35 secondi; ciascuna invocazione CLI circa
0,34–0,52 secondi, includendo avvio del client, handshake e salvataggio degli
output. Questi tempi non misurano una richiesta LLM o la Workforce completa
e non costituiscono un benchmark con ripetizioni.

## Punti da risolvere prima del collegamento agli agenti

**Identità software.** `log4j-core` produce diversi candidati, tra cui
`Apache Log4j Core`, altre varianti di Log4j e un prodotto hotpatch. Anche la
ricerca `Apache Log4j` con vendor esplicito mantiene due candidati `high`, con
vendor `Apache Software Foundation` e `Apache`. Una confidenza alta non elimina
necessariamente l'ambiguità. L'adapter dovrà conservare il nome osservato e
documentare separatamente l'eventuale risoluzione verso un'identità del KG,
senza riscrivere `RuntimeEvidence`.

**Regole non confrontabili.** Il record di `CVE-2021-44228` contiene:

```json
{
  "version": "2.0-beta9",
  "status": "affected",
  "version_type": "custom",
  "less_than": "log4j-core*"
}
```

Lo stesso limite superiore compare nell'OWL, nell'asserzione `hasLessThan`
di `CVE-2021-44228_Containers_Cna_Affected_Versions`, riga 23420392.
La risposta conserva anche i cinque cambi di stato presenti nella regola;
il valutatore non riesce a confrontarne il limite superiore e restituisce
`not_evaluable`, con motivazione `no version rule was comparable`.
Anche le regole delle altre due CVE associate a `Apache Log4j2` non vengono
valutate per la richiesta provata.

Non sono stati corretti i dati né modificato il motore per forzare un finding.
Occorre chiarire con l'autore la rappresentazione delle versioni e la loro
interpretazione prevista, confrontandole con i record originali e la procedura
di conversione. La concordanza tra OWL e SQLite non dimostra la correttezza
del valore né identifica l'origine del problema.

Il collegamento alla Workforce richiede un mapping per identità ambigue,
regole non valutabili e dati assenti, mantenendo distinti i tre artefatti.
Il trasporto è collaudato; l'adapter reale di dominio non è ancora attivo.

## Evidenze e riproducibilità

Controlli sui file:

```text
output/cti-dataset-inspection-20261005T100411Z-3d3e3cac/
```

`manifest.json` registra la prima ispezione, ancora bloccata sul puntatore LFS.
`download-receipt.json` documenta il recupero successivo; `sqlite-inspection.json`,
`log4j-rules.json` e `owl-selected-version-assertions.txt` conservano i controlli.

Prova conclusa:

```text
output/cti-real-smoke-20261005T101110Z-f74ed28d/
```

Ogni caso conserva richiesta, risposta e audit. `summary.json` contiene comandi,
tempi ed esiti. `reproduce.py` ripete la prova su questi percorsi locali in una
nuova directory e termina il server alla fine. È un launcher di collaudo, non
un componente importato dalla Workforce. Usa l'interprete `.venv` di `tesi`;
non dimostra un'installazione backend autonoma o un deployment su un altro host.

La prima prova, `output/cti-real-smoke-20261005T101004Z-486bd0c4/`, è conservata
come fallita: il nome del caso negativo conteneva `thesis` e il matcher trovava
un candidato `Online Thesis Archiving System` con confidenza `needs_review`.
È stato modificato soltanto l'input di quel caso, usando un identificativo
senza token condivisi; dati e algoritmo sono rimasti invariati.

Per una singola prova, dalla radice del backend:

```sh
PYTHONPATH=app/src /Users/reucalion/tesi/.venv/bin/python -m cti_mcp.server \
  --sqlite app/data/cve2owl_20260523_143950.affected.sqlite \
  --dataset-id cve2owl_20260523_143950 --dataset-kind real
```

Quindi, dalla radice di `tesi`, usando una nuova directory:

```sh
.venv/bin/python -m thesis_agents.mcp.cti_probe \
  --url http://127.0.0.1:8003/mcp --expected-kind real \
  --product 'Apache Log4j2' --vendor 'Apache Software Foundation' \
  --version 2.14.1 --evidence-id real-E1 \
  --output-dir output/cti-real-manual-01
```

Il servizio manuale si termina con Ctrl-C. I server avviati dalle prove
documentate sono già terminati. Nessun sorgente del backend è stato modificato.
