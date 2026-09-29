# Guida pratica alla demo e all'esposizione

Durata complessiva: **15 minuti**, di cui 4 per la demo e circa 1 per domande.
Le note del relatore sono già nel PowerPoint; il [copione delle slide](copione-slide.md)
le rende leggibili anche senza PowerPoint. Questa guida descrive cosa aprire
e cosa dire durante la parte pratica. Non è il resoconto di una nuova inferenza.

## Prima dell'incontro

1. Apri [presentazione.pptx](presentazione.pptx) e verifica la modalità relatore
   sullo schermo che userai. Le slide 11–12 sono appendici facoltative.
2. Apri [demo-evidenze.html](demo-evidenze.html) nel browser. Funziona offline e
   contiene copie degli output registrati, non un simulatore né un LLM.
3. Apri un terminale nella radice `tesi`, con il progetto già installato.
4. Avvia Ollama e controlla che il profilo esista:

```bash
ollama list
curl --max-time 5 http://localhost:11434/api/tags
```

Il nome da trovare è `tesi-qwen3:4b`. I comandi sopra controllano disponibilità
del servizio e del modello; non eseguono inferenza e non ne caricano i pesi.
Preparazione del modello e dell'ambiente: [guida del progetto](../../README.md).

Se vuoi fare una prova generale, esegui in anticipo il comando live sotto.
Apri il `summary.md` del nuovo batch: deve indicare un run verificato.
Una prova generale è un nuovo esperimento, con un proprio output; non sostituire
o modificare i risultati della matrice registrata per farli coincidere.

Non installare dipendenze e non scaricare modelli durante l'incontro.
Per controllare soltanto i contratti senza Ollama puoi usare:

```bash
.venv/bin/python -m thesis_agents.demo --mode fixtures --repetitions 1
```

Dichiara esplicitamente che `fixtures` non esegue gli agenti LLM.

## Scaletta dei 15 minuti

| Minuti | Slide | Punto da comunicare |
|---|---|---|
| 00:00–01:40 | 1–2 | Problema, obiettivo e caso illustrativo |
| 01:40–03:00 | 3 | DAG e convergenza dei tre artefatti |
| 03:00–05:15 | 4–5 | CAMEL/LLM reali e confine di validazione |
| 05:15–07:10 | 6–7 | Ranking, ammissibilità e componenti mock |
| 07:10–11:10 | 8 | Demo guidata |
| 11:10–14:00 | 9–10 | Risultati, recuperi, limiti e prossimo passo |
| 14:00–15:00 | eventuali appendici | Domande |

## Demo: quattro minuti, senza cercare file al momento

### 00:00–00:20 — Avvia il caso nominale

Dalla radice del repository:

```bash
.venv/bin/python -u -m thesis_agents.demo --mode camel --repetitions 1 \
  --scenarios demo_01_nominal --timeout 180
```

Il runner imposta esplicitamente Ollama locale e crea una directory nuova.
`--timeout 180` limita il processo a tre minuti per lasciare spazio al commento.
La matrice sperimentale usava invece 300 secondi: questo limite più breve è
una scelta per la presentazione, non una modifica dei contratti degli agenti.

**Frase suggerita:** «Ora avvio una nuova esecuzione CAMEL con il modello locale.
Durante l'attesa mostro gli artefatti di una prova già registrata, indicata come
tale. Il nuovo run sarà un risultato valido solo dopo i controlli del runner».

### 00:20–01:20 — Mostra i tre produttori

Nel visualizzatore offline seleziona **Nominale**, poi **Input** e **Tre artefatti**.
Mostra soltanto i campi principali:

- `RuntimeEvidence`: `service_name`, pacchetto/versione e `evidence_id`.
- `VulnerabilityReport`: `lookup_status`, CVE, `source` ed `evidence_ids`.
- `CandidateStrategies`: ID, azione e stime della prima candidata.

**Frase suggerita:** «La vulnerabilità è correlata al software osservato. Il
report conserva il riferimento all'evidenza ma non la sostituisce. Lo Strategic
riceve separatamente questi tre risultati. La fonte del lookup è una fixture».

### 01:20–02:05 — Spiega il rifiuto e il fallback

Seleziona **Senza manutenzione**, poi **Ranking e validazioni**.
Mostra il tentativo di `S_UPGRADE` con `missing_requirements: ["maintenance_window"]`
e il successivo `S_MONITOR` accettato.

**Frase suggerita:** «Un punteggio alto non supera un vincolo operativo. Il primo
candidato è rifiutato e lo Strategic passa al successivo. Il monitoraggio è
consentito dal mock, ma non elimina la vulnerabilità».

Questa scelta è osservata nei run LLM registrati. Le fixture prefissate scelgono
invece `S_ISOLATE`: non confondere i risultati delle due modalità.

### 02:05–02:45 — Confronta due esiti senza selezione

Seleziona **Tutte le azioni vietate** e mostra i quattro rifiuti, poi
**Lookup non supportato** e la decisione `insufficient_evidence`.

**Frase suggerita:** «Nel primo caso tutte le candidate pubblicate sono vietate.
Nel secondo mancano dati nel lookup. Non trovare una corrispondenza non significa
che il software sia sicuro o che nessuna contromisura possa esistere».

### 02:45–03:40 — Torna al nuovo run

Controlla il terminale e apri il `summary.md` indicato dal runner.

- Se il run è `verified=True`, mostra `artifacts/final_decision.json` nella
  **nuova** directory: selezione, `explanation_claims` e `agent_commentary`.
- Se il run è ancora attivo, continua con il materiale registrato. Il limite
  esterno lo interromperà al terzo minuto del processo.
- Se fallisce o va in timeout, dichiaralo e mostra il riepilogo parziale.
  Non riclassificarlo come `no_valid_strategy` o `insufficient_evidence`.

Per aprire il riepilogo usa il percorso stampato, senza indovinare quale sia la
cartella più recente fra gli output storici. Il visualizzatore HTML rimane
sempre sui risultati registrati: non si aggiorna automaticamente con il live.

### 03:40–04:00 — Chiudi la demo

**Frase suggerita:** «La spiegazione controllata cita gli artefatti. Il commento
originale dell'LLM è conservato come non verificato. La provenienza registra
file, hash e attività locali; non è ancora una transazione Fabric».

Torna alla slide 9 per discutere la matrice completa. Non avviare otto run live:
la matrice registrata ha richiesto circa sedici minuti e venticinque secondi.

## Domande probabili e risposte brevi

**Dove viene realmente usato CAMEL?**  
In `build_workforce`, che crea i quattro `ChatAgent`, collega i tool e registra
task e dipendenze. La Workforce esegue le chiamate LLM e gestisce i recuperi.

**Perché usare un LLM se alcuni passaggi sono deterministici?**  
La generazione delle candidate e il coordinamento delle chiamate sono affidati
agli agenti. Lookup, ranking e vincoli restano tool controllabili. Il prototipo
valuta questo confine; non dimostra ancora un vantaggio rispetto a ogni alternativa.

**Pydantic impedisce le allucinazioni?**  
Controlla struttura e vincoli dichiarati. La sessione verifica anche coerenza
fra artefatti. Le frasi libere possono ancora essere imprecise: per questo il
commento LLM è separato dalla spiegazione derivata dalle fonti.

**Il BWAF è già implementato? E Tiny-ME?**  
Sono ancora mock: somma pesata a un passo e controlli di capacità/policy.
Gli adapter verso i backend reali richiedono l'analisi delle rispettive API.

**Da dove viene la formula di score?**  
È un'euristica del mock: `(1 + beneficio - impatto) / 2` normalizza la
differenza in `[0,1]`, assegnando uguale peso ai due contributi. Non deriva da
un paper BWAF o dal contratto privato, e i coefficienti non sono calibrati su
dati. Serve a provare il flusso. Fonti e confronto con le baseline sono in
[fonti e scelte](../fonti-e-scelte.md).

**MCP e blockchain dove sono?**  
Non sono ancora nel percorso applicativo. I tool sono funzioni locali; la
provenienza è JSON con hash, senza firme o transazioni Fabric.

**Otto run su otto significa che il sistema è affidabile?**  
Dimostra il completamento verificato di questa matrice. Sono stati necessari
alcuni recuperi e il campione è piccolo. Non è una misura generale di affidabilità.

**Qual è il contributo attuale?**  
Un prototipo CAMEL eseguibile con DAG esplicito, artefatti distinti, controlli
di pubblicazione e un protocollo di prova riproducibile per le integrazioni successive.

**Qual è il prossimo passo?**  
Concordare con il docente il primo backend da integrare e i criteri di valutazione,
poi procedere con un adapter alla volta mantenendo i test di contratto.
