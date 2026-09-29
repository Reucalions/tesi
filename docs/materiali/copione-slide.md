# Copione delle slide

14 minuti + 1 minuto per domande. Le appendici sono facoltative.

## 1. Dalle evidenze a una proposta verificabile

00:00–00:45

L'obiettivo è mostrare un prototipo eseguibile che passa da dati su un servizio a una proposta di contromisura verificabile. Gli agenti CAMEL e il modello locale sono effettivamente utilizzati; i servizi esterni sono ancora simulati. La domanda di questa fase è se gli agenti riescano a collaborare rispettando contratti e provenienza delle evidenze. Le otto prove riguardano quattro scenari dimostrativi: non sono una misura generale di affidabilità. Nessuna contromisura viene eseguita sull'infrastruttura.

## 2. Una vulnerabilità non basta per scegliere un'azione

00:45–01:40

Il caso parte da un input statico, non da OpenTelemetry già collegato. Il servizio e il pacchetto sono associati a una vulnerabilità dal lookup mock. Questa informazione non basta a scegliere una risposta: occorre sapere quali azioni siano possibili e consentite. Per esempio, una proposta di upgrade non è ammissibile se manca la finestra di manutenzione. Separare evidenza, correlazione e vincoli permette di spiegare un eventuale rifiuto e la scelta successiva.

## 3. Tre artefatti convergono nello StrategicAgent

01:40–03:00

Telemetry pubblica RuntimeEvidence. Vulnerability ne usa software e versione per il lookup e pubblica un report separato. Countermeasure usa entrambi per generare strategie. Lo Strategic legge tutte e tre le chiavi del contesto, senza affidarsi soltanto al riepilogo dell'ultimo task. Nella pipeline i prerequisiti producono un ordine sequenziale, ma un artefatto non sostituisce il precedente. I produttori restano indicati nel contesto e nella provenienza. Il diagramma rappresenta dipendenze logiche, non messaggi inviati su una rete esterna.

## 4. CAMEL esegue gli agenti, Ollama genera le chiamate

03:00–04:10

I file in agents definiscono prompt e tool, mentre gli oggetti ChatAgent sono creati in workforce.py. Ogni worker riceve soltanto i tool del proprio ruolo. Il modello locale, tesi-qwen3:4b, interpreta le istruzioni ed effettua tool calling reale. Il CountermeasureAgent è il principale punto di generazione delle alternative. I tool deterministici calcolano ranking e ammissibilità. Sono presenti anche modelli gestionali CAMEL: le richieste LLM non corrispondono quindi a una sola chiamata per ciascuno dei quattro ruoli.

## 5. Un messaggio di successo non crea un artefatto

04:10–05:15

Gli artefatti autorevoli sono modelli Pydantic pubblicati mediante tool e salvati come JSON. Pydantic controlla la struttura; ArtifactSession applica anche confronti fra input e output. L'handler del task impedisce che un semplice messaggio DONE mascheri una pubblicazione mancante. Questo caso è stato osservato realmente nel secondo run nominale: mancavano decisione e provenienza, il primo tentativo è stato respinto e CAMEL ha recuperato. La validazione strutturale non dimostra la verità di qualsiasi frase generata.

## 6. Classificare una proposta e accettarla sono due passi

05:15–06:20

Il grafo rappresenta beneficio come supporto e impatto operativo come attacco. Il ranking mock applica la formula mostrata e risolve i pareggi per ID. Le stime di ingresso vengono dall'LLM, quindi un calcolo deterministico non rende oggettivi i punteggi. Lo Strategic prova poi le candidate in quell'ordine. La validazione controlla capacità e divieti; al primo successo ci si ferma. L'accettazione non dimostra l'efficacia in produzione. Per esempio, il monitoraggio può essere consentito pur non eliminando la vulnerabilità. Origine: (1 + beneficio - impatto) / 2 normalizza una differenza da [-1,1] a [0,1]. I pesi non sono calibrati su dati o derivati da un paper. Riferimenti teorici, distinti dalla formula: [BWAF-MN] e [BWAF-P], in docs/riferimenti/README.md. Il backend privato [BASE-LEDGER] richiama una libreria C++ distinta.

## 7. Che cosa è già reale e che cosa è simulato

06:20–07:10

CAMEL non è rimandato alla fase finale: è già in esecuzione. Ciò che manca sono gli adapter verso i servizi esterni. La presenza della dipendenza MCP nell'ambiente non significa che i tool siano già esposti via MCP. Analogamente il grafo didattico non equivale al BWAF finale, e il file di provenienza non è una transazione Fabric. Questa distinzione delimita il contributo del mockup: verificare collaborazione e contratti prima di aumentare la complessità delle integrazioni.

## 8. Demo · seguire una decisione fino alle sue fonti

07:10–11:10

Seguire il copione in demo-guida.md. Avviare il comando nel terminale dalla radice del repository. Durante l'attesa aprire le evidenze registrate, dichiarando che provengono dalla matrice del 16 settembre. Mostrare il nominale e il fallback senza manutenzione. Poi tornare al terminale: se il run termina, aprire il nuovo riepilogo; se è ancora attivo al limite del tempo assegnato, passare al materiale registrato e dichiararlo. La matrice completa ha richiesto oltre sedici minuti e non va eseguita dentro questa presentazione. Nessun risultato nuovo deve essere annunciato prima dei controlli del runner.

## 9. Otto prove complete, con recuperi osservati

11:10–12:50

Tutti gli otto run hanno completato gli artefatti e superato l'audit. Nel nominale della seconda ripetizione lo Strategic ha recuperato dopo aver omesso decisione e provenienza. Nei due casi non supportati il quality check CAMEL ha chiesto tre e due retry, giudicando insufficienti output vuoti che erano corretti per lo scenario. Nel primo è stata respinta una chiamata di validazione su ranking vuoto. Quindi otto su otto non significa assenza di errori intermedi. La misura è riferita a questi casi e non rappresenta una percentuale di affidabilità generale. I 95 test verificano soprattutto contratti e integrazione SDK, non la qualità scientifica delle proposte.

## 10. Il prossimo passo è validare le integrazioni

12:50–14:00

Il risultato di questa fase è un prototipo osservabile, nel quale posso seguire produttori, chiamate e motivi di una decisione. Restano aperte la qualità delle candidate, una valutazione su più casi e la gestione dei quality check sugli esiti vuoti. Proporrei di concordare con il docente quale backend collegare per primo e quali esperimenti debbano sostenere la tesi. L'integrazione richiederà la verifica delle API e delle ontologie nei repository reali. Chiudere lasciando circa un minuto alle domande; usare le due slide di appendice solo se utili.

## 11. Appendice · tre significati di “nessuna selezione”

Appendice

Da usare se viene chiesto che cosa accade quando manca una soluzione. La mancanza di copertura del lookup non dimostra assenza di vulnerabilità né mancato supporto del vendor. Tutte le candidate rifiutate significa tutte quelle generate in quel run, non ogni contromisura possibile nel mondo reale. Un timeout non viene convertito in un esito di dominio positivo.

## 12. Appendice · spiegazione controllata e commento LLM

Appendice

Questa separazione è stata introdotta dopo aver osservato versioni consigliate o deduzioni prive di fonte nelle risposte LLM. Il commento resta conservato, ma non viene promosso a spiegazione verificata. I riferimenti non bastano da soli: la sessione ricostruisce i claim e li confronta. Le descrizioni e i rationale delle candidate restano testo da esaminare criticamente.
