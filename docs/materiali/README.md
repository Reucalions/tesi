# Materiali per l'incontro con il docente

Il percorso di studio corrente e nell'[indice della documentazione](../README.md).
La pulizia del repository ha aggiornato i collegamenti nei sorgenti Markdown,
senza rigenerare Word, PDF, slide o figure. Il manifest del 29 ottobre descrive
gli export e i sorgenti al momento della loro generazione; i nuovi collegamenti
Markdown non sono una nuova versione degli export.

## Versione aggiornata per lo studio — 29 ottobre 2026

Il punto di ingresso corrente è [stato del progetto](../stato-progetto.md).
La revisione aggiunge le integrazioni Apache/Ubuntu, il ramo strategico senza
candidate, la prova Ollama e i collegamenti nativi Fabric predisposti. Le
ultime prove citate rimangono quelle del 18 ottobre: non sono nuove inferenze.

| File corrente | Uso |
|---|---|
| [relazione-aggiornata-20261029.docx](relazione-aggiornata-20261029.docx) | Copia completa del report manuale, con nota di lettura, capitoli 19–24 e nuove figure |
| [aggiornamento-relazione-20261029.md](aggiornamento-relazione-20261029.md) | Sorgente modificabile dei soli capitoli aggiunti |
| [aggiornamento-relazione-20261029.pdf](aggiornamento-relazione-20261029.pdf) | PDF dei soli capitoli aggiunti, per lettura; non è l'export dell'intero nuovo DOCX |
| [architettura-aggiornata.png](architettura-aggiornata.png) | Nuova figura dei componenti e dei collegamenti, con livelli di verifica |
| [architettura-aggiornata.svg](architettura-aggiornata.svg), [PDF](architettura-aggiornata.pdf) | Figura vettoriale, SVG con font incorporati |
| [confronto-mockup-attuale.png](confronto-mockup-attuale.png) | Confronto visivo con il mockup; disponibili anche SVG e PDF con lo stesso nome |
| [aggiornamento-verifica-20261029.json](aggiornamento-verifica-20261029.json) | Hash dei materiali e controllo di conservazione della relazione originale |

La copia manuale `relazione.docx` è rimasta invariata durante la generazione.
Sono conservati nella nuova copia tutti i **259 elementi originali del corpo**
(paragrafi, tabelle e proprietà della sezione) e le **due immagini preesistenti**.
Una nota prima della sintesi distingue capitoli storici e stato corrente.
La nuova figura è uno schema architetturale: non è un BWAF con strategie
selezionate. Il BWAF del run Apache è vuoto.

Il PDF dell'aggiornamento e le figure sono stati generati e ispezionati.
Il DOCX è verificato strutturalmente; la resa e l'impaginazione nativa vanno
controllate nell'editor Word utilizzato per la consegna. La nuova copia contiene
le revisioni manuali del documento base; il vecchio `relazione.pdf` e le slide
non rappresentano lo stato del report aggiornato.

Per rigenerare soltanto gli export aggiornati, in un ambiente con le dipendenze
di `requirements.txt`:

```sh
python docs/materiali/genera_aggiornamento.py \
  --base-docx docs/materiali/relazione.docx \
  --output-dir docs/materiali
```

Il comando non invoca `genera_materiali.py` e non sovrascrive il documento base.
Sovrascrive invece gli export datati prodotti dal nuovo generatore: conservare
con un altro nome eventuali successive correzioni manuali alla copia aggiornata.
`--output-dir` consente una destinazione diversa. Nessuna rete o inferenza viene
utilizzata dal generatore; i font PT Sans provengono dalla cartella già inclusa.

## Materiali storici dell'incontro sul mockup

Pacchetto preparato per **15 minuti**, con PowerPoint modificabile e demo locale.
Non sono state avviate nuove inferenze per preparare questi materiali.

La relazione modificata manualmente in `relazione.docx` è stata proseguita con
i capitoli 11–18, relativi alle integrazioni e alle prove successive. I capitoli
precedenti, le immagini e gli stili sono conservati. Il solo testo aggiunto è
in [integrazione-relazione.md](integrazione-relazione.md). `relazione-mockup.md`
resta il sorgente della versione precedente e non contiene le revisioni manuali:
non rigenerare il DOCX con `genera_materiali.py`, perché le sovrascriverebbe.
Il PDF e le slide restano alla versione precedente; l'esportazione del DOCX
integrato tramite Word è terminata per timeout. La copia precedente e il
confronto strutturale sono conservati localmente in
`output/relazione-integrazioni-verifica/`.

| File | Uso |
|---|---|
| [presentazione.pptx](presentazione.pptx) | 10 slide principali + 2 appendici, testo e diagramma modificabili, note del relatore |
| [relazione.pdf](relazione.pdf) | Export storico della relazione sul mockup, non aggiornato alle integrazioni |
| [relazione.docx](relazione.docx) | Base manuale con capitoli 1–18, conservata senza modifiche in questa revisione |
| [relazione sorgente](../archivio/relazione-mockup.md) | Sorgente della versione mockup; non contiene le revisioni manuali successive |
| [copione-slide.md](copione-slide.md) | Note da esporre e tempi di ciascuna slide |
| [demo-guida.md](demo-guida.md) | Comandi, file da mostrare, gestione del live e domande probabili |
| [demo-evidenze.html](demo-evidenze.html) | Visualizzatore offline e interattivo di quattro run registrati |
| [evidenze/inventario.json](evidenze/inventario.json) | Provenienza delle copie e hash per confrontarle con gli originali |
| [Fonti e scelte](../fonti-e-scelte.md) | Origine della formula, attribuzioni e confronto con le baseline private |
| [Bibliografia](../riferimenti/README.md) | Paper, documentazione, repository e ambito della consultazione |

## Come usarli

1. Leggi la sintesi iniziale della relazione e il copione: adattane le parole
   al tuo modo di esporre e verifica i punti da discutere con il docente.
2. Apri il PowerPoint e prova la modalità relatore. Le note non sono testo da
   mettere sullo schermo: servono a guidare l'esposizione.
3. Apri il visualizzatore nel browser; non richiede server né rete. L'etichetta
   dichiara sempre che gli output sono registrati, non una nuova esecuzione.
4. Fai una prova generale usando la guida, fermando il discorso a 14 minuti
   per lasciare un minuto alle domande.

Nella demo viene avviato un solo caso live, con limite di processo a 180 secondi.
I confronti usano copie immutate dei nove JSON delle quattro ripetizioni `r1`
del batch `output/demo-matrix-20260916T074247Z-80665fa1/`. La sintesi della matrice
comprende anche `r2`; i relativi artefatti e i log completi restano nel batch
originale. I file inclusi non contengono `.env`, chiavi o conversazioni SDK.

I numeri delle slide sono quelli della matrice documentata: **8/8 run verificati,
95 test passati prima della matrice, 212 richieste LLM e 985,35 secondi**.
Non vanno presentati come risultati di una nuova esecuzione fatta durante l'incontro.

## Modifica e rigenerazione dei materiali storici

Puoi modificare direttamente PowerPoint e Word. Per una rigenerazione coerente,
modifica invece `slides.json` e `../archivio/relazione-mockup.md`; il generatore sovrascrive
gli export, quindi conserva separatamente eventuali modifiche manuali ai binari.
I dati del frontespizio della relazione sono in `frontespizio.json`.
Le fonti bibliografiche sono in `../riferimenti/fonti.json`; il comando
`python3 docs/riferimenti/aggiorna_fonti.py` aggiorna catalogo, BibTeX e
bibliografia della relazione prima di rigenerare gli export.

Le dipendenze di impaginazione sono separate da quelle del prototipo:

```bash
python3.12 -m venv /tmp/tesi-materiali-venv
/tmp/tesi-materiali-venv/bin/python -m pip install -r docs/materiali/requirements.txt
/tmp/tesi-materiali-venv/bin/python docs/materiali/genera_materiali.py
```

Il generatore usa i file PT Sans inclusi in `fonts/`, senza dipendere dai font
installati per produrre il PDF. Dopo una modifica controlla l'impaginazione sul
computer di destinazione. `viewer.template.html` è il sorgente del visualizzatore;
i dati vengono incorporati dai JSON in `evidenze/`, senza chiamate di rete.

`architettura.pdf` e `architettura.png` sono figure generate per la relazione.
Il diagramma nella presentazione è composto da forme e connettori modificabili.
Gli export Word/PDF conservano gli elenchi numerati e contengono una tabella dei
percorsi interni, consultabile anche senza collegamenti attivi. Il Markdown
conserva i collegamenti relativi al repository.

## Tipografia ispirata al Politecnico di Bari

Relazione, diagramma e PowerPoint usano **PT Sans**; titoli e accenti usano
l'ottanio **#008195** (RGB 0, 129, 149). Il riferimento è il
[Piano della comunicazione Poliba 2022, sezione «Il Marchio completo», p. 46](https://www.poliba.it/sites/default/files/piano_comunicazione_2022_3_aprile_2022.pdf):
PT Sans Regular è la base del lettering del logotipo, successivamente modificato.
Questa impaginazione si ispira al marchio: non è un template ufficiale di tesi.
Il frontespizio della relazione include il
[logo ufficiale dal sito dell'Ateneo](https://www.poliba.it/sites/default/files/logo_poliba_orizzontale_ufficiale.png),
conservato in `assets/logo-poliba.png` senza alterarne le proporzioni.
La fonte e l'hash sono registrati in `assets/sources.json`.
I comandi nella relazione
mantengono un carattere monospaziato per facilitarne la lettura.

**Il PDF incorpora il font. Per Word e PowerPoint installa PT Sans** sul computer
usato per modificare o presentare i documenti, per evitare sostituzioni automatiche.
I file Office specificano PT Sans anche nel tema, ma non incorporano i file TTF.
Su macOS seleziona i quattro `.ttf` in [fonts/](fonts/), aprili con Libro Font e
scegli «Installa»; poi riapri Word/PowerPoint. Su Windows selezionali e scegli
«Installa» dal menu contestuale.

I font provengono dal [repository Google Fonts](https://github.com/google/fonts/tree/main/ofl/ptsans)
e sono distribuiti insieme alla [licenza SIL OFL](fonts/OFL.txt).
[sources.json](fonts/sources.json) contiene URL e SHA-256 dei file inclusi.

## Verifiche dei materiali

Sono stati controllati contenuti e note delle 12 slide, durata del copione,
posizioni degli elementi e impaginazione della relazione PDF. Il visualizzatore
è stato aperto nel browser; le copie degli artefatti sono confrontate con gli
hash originali e rilette con i modelli Pydantic. Non sono nuovi test del modello LLM.

L'esportazione automatica delle slide tramite Keynote è andata in timeout:
non è incluso un PDF delle slide. Il PowerPoint modificabile è disponibile;
la verifica finale della resa nativa va fatta aprendolo in PowerPoint sul
computer della presentazione. L'anteprima delle coordinate non sostituisce
quel controllo. La relazione PDF è invece stata generata e ispezionata.

Dopo il passaggio a PT Sans sono state ricontrollate le 12 slide e le metriche
del testo: nessuna eccedenza stimata nei riquadri.
Il PDF contiene PT Sans incorporato e i temi Word/PowerPoint usano la stessa
famiglia. Il simbolo di freccia testuale nella tabella dei risultati è stato
sostituito con «poi», perché non è presente nel font; il significato è invariato.

La relazione per l'invio al docente include un frontespizio con Ateneo, logo,
titolo, corso, autore, relatore e data. Sono state eliminate tutte le diciture
a piè di pagina, compresa la numerazione. La revisione conserva i risultati
della matrice storica e distingue implementazione effettiva, servizi simulati
e integrazioni future. Il PDF è stato ricontrollato dopo la revisione; la copia
DOCX è modificabile e può impaginarsi diversamente in base all'applicazione.
