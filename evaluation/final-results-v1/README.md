# Risultati finali congelati — v1, 13 novembre 2026

Questo pacchetto conserva nel repository le misure necessarie alle tabelle della
[valutazione finale](../../docs/tecnica/valutazione-finale.md). I file sono pronti
per il versionamento; questa fase non crea commit o push.

- `results.json`: risultati e limiti delle campagne, statistiche per coorte.
- `series.csv`, `statistics.csv`: 227 timer osservati e sintesi con n, minimo,
  mediana, massimo e deviazione standard campionaria (nulla per n=1).
- `comparisons.csv`, `paired-statistics.csv`: 30 confronti contratto nativo in
  memoria/MCP e 15 coppie REST evaluate/invoke; differenze firmate.
- `case-outcomes.csv`: quattro launcher primari, con tempi ed esiti distinti.
- `coverage.json`, `coverage.csv`: le 32 voci della proposta, evidenze e limiti.
- `inventory.json`, `inventory.csv`: 3293 file univoci con SHA-256 e gruppi;
  copie annidate di lineage non sono osservazioni indipendenti.
- `input-manifest.json`: hash degli 84 ingressi letti dal consolidamento.
- `source-inputs.tar.gz`: quegli ingressi e i protocolli/collector necessari a
  comprendere questa campagna (102 file, percorsi relativi, senza credenziali).
- `protocol.json`: confini della sintesi; `manifest.json`: hash del pacchetto.

Dalla radice del repository, senza servizi, dataset esterni o dipendenze extra:

```bash
python3 -m evaluation.verify_final_bundle
```

Il comando verifica hash, estrae in una directory temporanea controllata e
ricalcola tutte le tabelle con `evaluation/consolidate_final.py`, riusando
l'inventario congelato. Confronta byte per byte gli artefatti numerici. Il
manifest viene verificato prima del ricalcolo; non e una firma o una prova di
validita scientifica delle etichette. L'archivio e una selezione per ricalcolare
la sintesi, non un backup completo dei repository, del KG o della blockchain.

Gli archivi completi locali sono `output/final-evaluation-20261113-r1/`,
`output/component-metrics-20261112-r1/`, i due benchmark distinti del 12 e 13
novembre, e `output/case-improvements-20261106/`. Prove complete, tentativi
falliti, metadati SaaS e output nativi restano li. Le riletture live fresche
sono gia eseguite; questo verificatore offline non le simula o ripete.

Limiti: riferimento assistito senza revisione umana indipendente, nessuna
accepted/fallback applicativa C1/C4, pesi iniziali dei nodi non esposti,
spiegazioni parziali, confronto runtime al confine degli artefatti, campioni
piccoli e nessun isolamento del solo consenso, del solo PROV-O o del tempo
originale evento-decisione. Nessuna percentuale globale di conformita.
