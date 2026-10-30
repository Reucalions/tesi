# CountermeasureAgent: verifiche pendenti per il caso Apache

Il CountermeasureAgent ora distingue le **strategie di mitigazione**, riferite
ai finding confermati, dalle **richieste di evidenza**, necessarie per chiarire
le classificazioni del pacchetto Ubuntu. Entrambe sono pubblicate nel suo
artefatto `candidate_strategies.json`, in campi separati:

```json
{
  "strategies": [],
  "verification_requests": []
}
```

Le liste nell'esempio illustrano il formato. Nel caso Apache reale
`verification_requests` contiene quattro richieste, con gli ID CVE completi,
stato `pending`, evidenze da ottenere e puntatori al report di origine.
Le richieste non hanno score o versione di upgrade scelta. Non diventano nodi
del grafo di argomentazione, elementi del ranking o contromisure selezionate.

## Preparazione e pubblicazione

Quando il report contiene `package_assessment`, `get_context` espone
`external_inputs.package_verification.required=true`. L'agente deve invocare
`prepare_package_verification({})`, rileggere il contesto e pubblicare tutte
le richieste restituite insieme alle eventuali strategie. Per Apache, la
lista delle strategie rimane vuota perché non vi sono finding runtime confermati.

Il tool prepara una lista ripetibile dalle classificazioni già validate.
Non acquisisce dati runtime, non consulta nuovi advisory e non verifica
effettivamente la compatibilità. La preparazione è deterministica; l'LLM
non inventa condizioni specifiche delle CVE o risultati delle verifiche.
Le strategie per i finding confermati conservano il precedente percorso
generativo e i controlli su capacità e policy.

Il file ausiliario `package_verification_context.json` conserva la lista
richiesta e i digest di telemetria, report e risposta Ubuntu integrale.
La sessione verifica snapshot e derivazione, richiede la preparazione prima
della pubblicazione e rifiuta omissioni, CVE estranee, richieste alterate,
esiti dichiarati completati e versioni di upgrade inventate. Un retry riusa
il contesto senza riscriverlo. Anche letture successive, decisione e verifica
finale ricontrollano l'integrità del contesto.

La provenienza collega la preparazione al CountermeasureAgent e agli
artefatti utilizzati. Rimangono gli otto artefatti principali; il contesto
è un file ausiliario. Il campo `verification_requests` viene omesso quando
vuoto, preservando la serializzazione storica dei casi senza queste richieste.
L'ingresso SBOM/OSV Maven precedente rimane disponibile; non viene presentato
come un inventario Ubuntu né viene interrogato nel nuovo profilo Apache.

## Collaudo con servizi reali

Il run locale `output/apache-ubuntu-countermeasure/` usa lo stesso profilo
`config/backends.otel-apache-ubuntu.json`: gateway OTel e MCP Ubuntu reali,
CAMEL con inferenza programmata, tool strategici mock locali. Nessun LLM.
Le 120 valutazioni per CVE coincidono con il run Vulnerability precedente.

| Richiesta pendente | CVE coinvolte | Evidenze richieste |
|---|---:|---|
| Stato storico del processo | 58 | Revisione effettiva, eseguibile e riavvii contemporanei ai log; riconciliazione con l'inventario successivo |
| Condizioni runtime | 46 | Per ogni CVE potenziale: prerequisiti dalle fonti, moduli, configurazione ed esposizione effettivi |
| Stato Ubuntu Bionic | 12 | Stato specifico della release con fonte e hash, oppure motivo dell'incertezza conservato |
| Compatibilità dell'upgrade | 46 | Percorso supportato, pacchetti disponibili, dipendenze, compatibilità applicativa, manutenzione, riavvio e rollback |

Sono **58 CVE uniche** da approfondire; i gruppi si sovrappongono. Le 34
`fixed` e le 28 `not_affected` sono escluse dalla lista di indagine pendente.
Le soglie di correzione per singola CVE non vengono trasformate in una
versione globalmente sicura o compatibile.

Lo StrategicAgent riceve le richieste nell'artefatto del Countermeasure e le
riporta come verifiche aperte nella spiegazione con riferimenti alle fonti.
Ranking e validazioni restano vuoti; la decisione è `insufficient_evidence`.
Nessuna verifica o mitigazione è stata eseguita.

Il [riepilogo](../output/apache-ubuntu-countermeasure/summary.json),
l'[output del Countermeasure](../output/apache-ubuntu-countermeasure/artifacts/candidate_strategies.json)
e la [verifica di conservazione](../output/apache-ubuntu-countermeasure/verification.json)
documentano il risultato. Gli output locali sono ignorati da Git. Come nel
collaudo precedente, i warning sulla valutazione gestionale CAMEL dipendono
dal modello programmato; il fallback non è una valutazione qualitativa LLM.

## Riproduzione e lavoro successivo

Avviare gateway e servizio Ubuntu come descritto nella
[guida VulnerabilityAgent](ubuntu-vulnerability-agent.md#riproduzione), poi
scegliere una directory di output nuova:

```sh
.venv/bin/python tests/support/otel_workforce_smoke.py \
  --input config/input.otel-apache-recorded.json \
  --backends config/backends.otel-apache-ubuntu.json \
  --output-dir output/apache-ubuntu-countermeasure
```

Restano da acquisire le evidenze richieste e da collaudare il comportamento
con Ollama. L'integrazione dei servizi reali dello StrategicAgent è il
successivo incremento separato: argomentazione, ranking, validazione semantica
e registrazione della provenienza richiedono contratti e prove dedicate.

Il successivo [incremento StrategicAgent](apache-strategic-agent.md) ha concluso
il ramo Apache senza candidate con astensione esplicita e archivio MCP
PROV-O verificato. I servizi BWAF/Tiny-ME/Fabric restano aperti; il nuovo
percorso non trasforma le richieste pendenti in strategie selezionabili.

Verifiche finali: **350 test superati**, inclusi 14 nuovi test sul percorso
Countermeasure, Ruff, formato, `git diff --check` e `pip check`. Il nuovo
payload richiede copia esatta delle richieste: una futura prova Ollama dovrà
verificare il budget di contesto e risposta. Il backend esterno è invariato.
