# Esito della revisione tecnica — 12 novembre 2026

Revisione dell’assistente su fonti e protocollo, effettuata su richiesta dell’utente. La v1 resta immutata. Nessuna nuova predizione, inferenza o chiamata a servizi.

**28/28 casi riesaminati; nessuna etichetta o ingresso modificato.** Precisati risoluzione dell’identita, casi dipendenti dalla policy e trattamento degli errori tecnici.

## Controlli sulle fonti

- Verificati i digest completi dell’OWL originale e del database SQLite congelati.
- Quattro export SDK confrontati byte per byte con le fonti originali.
- Dodici ingressi di estrazione confrontati con le tuple attese e le assenze dei campi.
- Trentatre literal OWL/SQLite concordanti; righe grezze correnti confrontate con le copie.
- Regole di versione, inclusivita, default e assenza di version changes riesaminati.

## Esiti per caso

| Caso | Verifica | Esito |
| --- | --- | --- |
| E01 | Fonte diretta / regola grezza | Tuple confermate |
| E02 | Fonte diretta / regola grezza | Tuple confermate |
| E03 | Fonte diretta / regola grezza | Tuple confermate |
| E04 | Fonte diretta / regola grezza | Tuple confermate |
| E05 | Fonte diretta / regola grezza | Tuple confermate |
| E06 | Fonte e policy esplicita | Tuple confermate |
| E07 | Fonte e policy esplicita | Tuple confermate |
| E08 | Fonte e policy esplicita | Tuple confermate |
| E09 | Fonte e policy esplicita | Tuple confermate |
| E10 | Fonte diretta / regola grezza | Tuple confermate |
| E11 | Fonte e policy esplicita | Tuple confermate |
| E12 | Fonte e policy esplicita | Tuple confermate |
| C01 | Fonte diretta / regola grezza | matched; vulnerable |
| C02 | Fonte diretta / regola grezza | matched; not_vulnerable |
| C03 | Fonte diretta / regola grezza | matched; vulnerable |
| C04 | Fonte diretta / regola grezza | matched; unknown |
| C05 | Fonte diretta / regola grezza | matched; unknown |
| C06 | Fonte diretta / regola grezza | matched; unknown |
| C07 | Fonte diretta / regola grezza | matched; unknown |
| C08 | Fonte e policy esplicita | ambiguous; not_evaluable |
| C09 | Fonte diretta / regola grezza | matched; vulnerable |
| C10 | Fonte diretta / regola grezza | matched; not_vulnerable |
| C11 | Fonte e policy esplicita | matched; vulnerable |
| C12 | Fonte diretta / regola grezza | matched; not_vulnerable |
| C13 | Fonte diretta / regola grezza | matched; vulnerable |
| C14 | Fonte diretta / regola grezza | matched; unknown |
| C15 | Fonte diretta / regola grezza | not_found; not_evaluable |
| C16 | Fonte e policy esplicita | not_found; not_evaluable |

## Chiarimenti importanti

- C08: ambiguita sotto la policy delle identita letterali, senza affermare diversita reale delle organizzazioni.
- C11: alias verificato sulla coordinata Maven della specifica identita Apache.
- C16: vendor vincolante; il prodotto esiste, ma non sotto il vendor sintetico richiesto.
- Un errore tecnico non e un unknown corretto; niente esclusioni a posteriori dai denominatori.

## Uso e limite della revisione

Il campione e congelato per una valutazione controllata con riferimento assistito verificato sulle fonti. Non occorre ripetere a mano i controlli tecnici. Resta assente una revisione umana indipendente: non dichiarare doppia annotazione, accordo fra annotatori o completo soddisfacimento del requisito di corpus annotato manualmente della proposta.

Le metriche restano nulle finche non saranno raccolte le predizioni. Denominatori confermati: 12 documenti, 16 query di matching, 13 versioni a tre classi e 8 binarie. Separare gli strati originali/sintetici e i tre casi di policy del matching.

[Protocollo v2](README.md) · [Scheda compilata](review.csv) · [Controlli](review-findings.json) · [Manifest](manifest.json)
