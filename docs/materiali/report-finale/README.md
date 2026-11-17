# Report accademico completo

- [Report PDF](report.pdf): **29 pagine complessive**, comprese copertina,
  sommario, conclusioni e bibliografia. È il documento impaginato di riferimento.
- [Report Word modificabile](report.docx): contenuto corrispondente, con stili
  di titolo, tabelle e quattro varianti PT Sans incorporate.
- [Testo consultabile](report.md) e [contenuto strutturato](contenuto.json).
- [Anteprima delle pagine](anteprima.png).

Frontespizio: Politecnico di Bari; insegnamento **Information Systems Design
and Big Data**; docente **Prof. Saverio Ieva**; autore Alessandro Costa.
Il carattere è PT Sans, coerente con i materiali del progetto; il logo ufficiale
conserva le proprie proporzioni. L'impaginazione non è presentata come un modello
ufficiale di tesi dell'Ateneo.

Il report comprende introduzione, problema e soluzione, realizzazione del mockup,
architettura completa, valutazione, conclusioni con limiti e sviluppi futuri.
Contiene sei figure e ventisei tabelle numerate, oltre alla tabella del sommario.
Il capitolo 5, alle pagine 16–20, segue una run completa C1: fonti, asserzioni OWL,
profili ALN, grafo, risposta Tiny-ME, vincoli operativi e finalizzazione.
Gli alias degli individui sono esplicitamente ricondotti ai nomi ontologici reali.
La narrazione non riporta cronologia operativa, nomi di file o identificativi
interni di repository/branch. Le due basi software sono descritte per funzione.
Le istruzioni e i percorsi in questa nota sono materiale editoriale separato.

La nomenclatura tecnica usa una gerarchia tipografica condivisa tra testo,
tabelle, didascalie e sei diagrammi:

- ruoli degli agenti e termini ontologici in **grassetto petrolio**;
- identificatori, stati, capacità, IRI e opzioni applicative in grassetto
  petrolio con fondo tenue;
- alias degli individui e delle attività in **grassetto corsivo petrolio**.

Il carattere rimane PT Sans. Le lettere isolate sono riconosciute soltanto nei
contesti semantici espliciti, senza evidenziare articoli o preposizioni comuni.
Le regole condivise sono in `tipografia.py`; i dati di `contenuto.json` rimangono
privi di marcatori di impaginazione. PDF e Word sono verificati anche su dieci
esempi rappresentativi di identificatori, termini e alias.

Il PDF incorpora PT Sans e utilizza figure vettoriali. Il DOCX incorpora i font
con licenza SIL OFL, disponibile nella cartella dei font dei materiali, e usa
interruzioni esplicite tra le unità del report. Il limite di pagine è verificato
sul PDF, entro il nuovo massimo di 30 pagine. Un tentativo di controllo nativo
da Word è andato in timeout; per questa revisione
non viene dichiarato verificato il conteggio nativo del DOCX. Una modifica del
contenuto o un diverso renderer può richiederne una nuova impaginazione.

## Generazione e verifiche

Usare un ambiente separato da quello del prototipo:

```bash
python3.12 -m venv /tmp/tesi-report-venv
/tmp/tesi-report-venv/bin/python -m pip install -r docs/materiali/report-finale/requirements.txt
/tmp/tesi-report-venv/bin/python docs/materiali/report-finale/genera_report.py
python3 docs/materiali/report-finale/verifica_dati.py
python3 docs/materiali/report-finale/verifica_caso.py
```

L’estratto del caso è conservato in `esempio-semantico.json`, con gli hash di
15 sorgenti appartenenti al medesimo percorso C1. `estrai_caso.py` permette di
ricrearlo in sola lettura dagli archivi originali, senza contattare i backend.
`verifica_caso.py` confronta alias, asserzioni OWL, restrizioni ALN, risultati
semantici/operativi, otto digest delle fonti, tre relazioni PROV e ricevuta.

Il generatore scrive esclusivamente in questa cartella. I documenti manuali
preesistenti rimangono invariati e i loro hash sono in `originali-protetti.json`.
Il PDF contiene segnalibri navigabili; Word usa stili di titolo per la navigazione.
Le figure sono disponibili separatamente in PDF vettoriale e PNG.

`verifica.json` controlla conteggio delle pagine PDF, collocazione dei titoli,
font realmente utilizzati e incorporati, tabelle Word, testo fuori pagina,
glifi mancanti e assenza dei riferimenti operativi esclusi. `fonti-dati.json`
registra le fonti numeriche e le tabelle confrontate con i risultati congelati.
Il controllo delle tabelle non esegue nuove prove, non modifica annotazioni e
non ricalcola gli esperimenti. I materiali sono stati anche ispezionati visivamente.
La versione precedente
di 24 pagine è conservata separatamente in
`output/report-semantico-r1/precedente-24-pagine/`.
La versione di 29 pagine precedente alla revisione tipografica è in
`output/report-tipografia-r1/precedente/`, con manifest degli hash.
`output/report-tipografia-r1/verifica-contenuti.json` attesta che narrativa
strutturata, testo Word e testo delle 29 pagine PDF non sono cambiati.
