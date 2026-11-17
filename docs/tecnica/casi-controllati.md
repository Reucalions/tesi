# Quattro casi controllati per la chiusura

## C4-r3: collaudo integrale riuscito il 12 novembre 2026

C4-r3 ha completato in un unico launcher tutti gli otto nodi del DAG originale,
fino a finalizzazione e rilettura: exit code 0, `dry_run_completed`, blocco 28,
validation_code=0. Il timeout LLM e 600 s; durata osservata 1224,254 s.
Nessuna ripresa manuale: gli eventuali retry sono quelli interni CAMEL.
[Report, DAG e verifiche](../../output/c4-collaudo-20261112-r2/report.md).

Esito `requires_prerequisites`, nessuna candidata selezionata. La policy segnala
maintenance_window e il prerequisito letterale `package_upgrade capability`,
distinto dal `package_upgrade` disponibile. Tiny-ME conserva abduzione 38 e
score 62. Nessun fallback dimostrato o modifica semantica per ottenere accettazione.
C1/C4 sono ora collaudati fino alla finalizzazione; C2/C3 conservano gli esiti
conclusi nei rispettivi percorsi di assessment. Gli stati sotto sono storici.

## C4: ripresa conclusa il 12 novembre 2026

C4-r2 conserva sette nodi completati nel launcher e l'ultimo fallito per timeout
Ollama dopo il commit. La finalizzazione e stata conclusa in una ripresa CAMEL
separata, con timeout 600 s e exit code 0; lo stesso commit nel blocco 25 e stato
riletto e confrontato integralmente via MCP. Il DAG originale non e stato riscritto:
questo esito non attesta un unico launcher C4 end-to-end riuscito.

Il caso dimostra `maintenance_window` mancante con `package_upgrade` disponibile;
esito `requires_prerequisites`, nessuna candidata selezionata, nessun fallback.
Tiny-ME conserva abduzione 38 e score 62; la semantica resta limitata come concordato.
[Report, verifiche e artefatti](../../output/c4-collaudo-20261112-r1/report.md).
Gli stati successivi sono storici; C1/C2/C3 restano quelli gia verificati.

## Chiusura C1 verificata: 7 novembre 2026

C1-r2 ha completato il launcher reale CAMEL/Ollama e tutti gli otto nodi del DAG
con `dry_run_completed` e finalizzazione condivisa `completed`.
Esito decisionale: **requires_prerequisites**, con `selected_strategy_id=null`.
Tiny-ME restituisce abduzione 38 e score 62; il controllo operativo restituisce
`requires_review`. Il completamento tecnico non attesta una contromisura accettata.
C2/C3 restano completati; C4 e i suoi tentativi di ripresa restano non completati.

[Report corrente](../../output/case-improvements-20261106/report-C1.md). Le sezioni datate sotto conservano la preparazione
e gli esiti precedenti; Logback e ora adottato nel protocollo v2.

Preparazione del 5 novembre 2026. Il perimetro resta congelato: riuso di input,
applicazione Java, parser, runner e backend esistenti. Nessuna nuova funzione di
ranking, estensione semantica o modifica dei repository esterni.

Aggiornamento del 6 novembre: realizzate le due build Java coerenti e avviati
rete Fabric e MCP effettivi. Il
[primo collaudo diagnostico](../../output/real-cases-20261105-r1/report.md) conserva
tentativi CAMEL/Ollama con fonti reali e relativi blocchi. Le indicazioni di
preparazione sotto descrivono il punto di partenza, non sostituiscono gli esiti
effettivi: non sono ancora quattro run del launcher completati fino alla finalizzazione.

L'[audit KG successivo del 6 novembre](../../output/kg-coverage-20261106/report.md)
conferma che le tre CVE Log4j non hanno rimedi. Propone Logback-core
1.5.24/1.5.25, con CTI completo e proiezione ALN verificati. Protocollo e input
esistenti restano invariati finche non viene adottata e osservata la nuova coppia.
La sola candidata di aggiornamento permette C4 senza azione accettabile in
assenza di manutenzione, ma non dimostra selezione di un'alternativa.

## Struttura comune e confronto con i mock

Ogni caso conserva input, provenienza delle fonti, variazione controllata, esito
atteso, comando eseguito e artefatti ottenuti. Il percorso dei produttori resta
Telemetry -> Vulnerability -> Countermeasure; se ci sono candidate, prosegue con
preparazione canonica, ranking, validazione, selezione e finalizzazione condivisa.
Gli esiti senza candidate terminano con un assessment e fasi native non applicabili.

| Caso | Analogo disponibile nel mock | Attesa nel percorso reale |
| --- | --- | --- |
| C1: vulnerabile | `demo_01_nominal`: selezione di S_UPGRADE | Finding fondati sullo snapshot; prima candidata effettivamente accettata, se presente, e finalizzazione/rilettura |
| C2: non vulnerabile nello snapshot | Input di confronto con versione 2.26.1: il mock restituisce unsupported | `no_findings` solo con identita risolta e copertura negativa completa; nessuna candidata o chiamata al ranking |
| C3: evidenza insufficiente | `demo_04_unsupported_lookup`: insufficienza di copertura | Identita CTI ambigua oppure valutazione non conclusiva; astensione, senza CVE o strategie inventate |
| C4: vulnerabile con vincoli | `demo_02_no_maintenance`: passa da upgrade a isolamento | Upgrade non accettabile senza manutenzione; alternativa se effettivamente accettata, altrimenti esito condizionato reale |

Il vecchio `demo_03_all_actions_prohibited` resta una regressione utile ma non
sostituisce il nuovo caso negativo: vietare azioni non rende il componente non
vulnerabile. Le quattro nuove categorie non coincidono quindi uno a uno con le
quattro demo storiche. Il mock esatto non viene esteso per ottenere un falso
confronto negativo: per C2 la differenza di esito e attesa e dichiarata.

Gli ID e gli score delle fixture non sono oracle dei servizi reali. Nel caso C4
si dimostra un fallback soltanto se una candidata precedente viene davvero
scartata e una successiva selezionata: proporre subito un'alternativa e coerente,
ma non dimostra quel passaggio. Prerequisiti operativi mancanti e incompatibilita
Tiny-ME restano valutazioni distinte.

## Materiale gia disponibile

Il [manifest dei casi](../../config/controlled-cases.v1.json) fissa input, catture
CTI, aspettative e preparazione residua per ciascun caso.

- C1/C4 riusano gli input statici nominale e senza manutenzione. Le catture CTI
  su `Apache Log4j Core 2.14.1` contengono tre finding, relativi a CVE-2025-68161,
  CVE-2026-34477 e CVE-2026-34480 nello snapshot conservato. Non vanno sostituiti
  con CVE-2021-44228 soltanto per replicare la fixture mock.
- C2 riusa l'applicazione e le fonti coerenti in
  [observed-app-sources-20261007-02](../../output/observed-app-sources-20261007-02/):
  versione caricata 2.26.1, JAR, SBOM, cinque record SDK, istanza e finestra temporale.
  La [cattura CTI](../../output/observed-app-workforce-20261007-01/artifacts/cti_assessment.json)
  conserva la valutazione negativa di quello snapshot, non una garanzia generale
  di sicurezza o un risultato dei servizi attuali.
- C3 riusa il riferimento mock non supportato e la cattura CTI gia disponibile
  per il nome `log4j-core 2.14.1`: il matcher restituiva piu identita non risolte.
  Il nome osservato non viene corretto silenziosamente dall'LLM. Assenza di
  endpoint/deserializzazione nei log, da sola, non significa che il lookup sia
  inconcludente: lo scenario deve rimuovere proprio l'informazione necessaria.

La documentazione [Apache](https://logging.apache.org/security.html) fornisce il
riferimento del produttore; il verdetto sperimentale e riferito alle regole,
versioni e CVE effettivamente valutate dal nostro snapshot.

## Preparazione residua delle fonti reali

La matrice e preparata; non sono ancora quattro run reali pronti o eseguiti.
Per C1 serve una raccolta coerente della build vulnerabile: riusare
[prepare.py](../../examples/observed-app/prepare.py) e l'applicazione Java in una
copia isolata, conservando il POM e i risultati storici. `inspect_sources` verifica
JAR caricato, SBOM, identita e finestra. La versione nel JSON statico non prova
quale libreria sia stata caricata. Il carico esistente registra operazioni locali;
nessuna esecuzione di exploit e necessaria.

C4 deve riusare le stesse fonti di C1: si rimuove soltanto `maintenance_window`
dalla policy. La lista delle capacita nell'input e quella del profilo di validazione
devono coincidere. Le capacita dichiarate per la prova sono assunzioni dell'operatore,
non attuatori dimostrati dalla telemetria e non autorizzano azioni reali.

Per C3 conservare fonte originale e variazione dichiarata della qualita dell'identita.
Se si altera una copia dell'export per riprodurre il nome ambiguo, il manifest deve
qualificarla come degradazione sintetica controllata. Un file mancante, un input
invalido o un timeout verifica un guasto tecnico e non sostituisce l'astensione.

C2 puo riusare l'archivio come replay dichiarato, con i timestamp e l'istanza
originali; per una coppia di nuove build, ripetere la raccolta nella versione
negativa gia fissata. Non mescolare SBOM della versione corretta e log della versione
vulnerabile. Non rinominare o modificare le fonti storiche.

Il profilo reale va completato da
[backends.real.example.json](../../config/backends.real.example.json), verificando
KG, digest e binding per tutte le coppie CVE/candidata effettive. L'esempio contiene
placeholder e binding illustrativi della demo: non e un profilo pronto e non si
copiano i suoi IRI come fatti. Disponibilita dei servizi e binding distribuiti si
verificano nella fase finale concordata.

## Esecuzione e raccolta

Per i riferimenti mock usare la CLI esistente, con directory nuove:

```sh
.venv/bin/python main.py --backend-mode mockup --mode fixtures \
  --input thesis_agents/data/demo_01_nominal.json \
  --output output/controlled-C1-mockup-r1
```

Gli altri input sono nel manifest. Per il percorso reale, dopo la preparazione
delle fonti e del profilo, il comando esistente e:

```sh
.venv/bin/python main.py --backend-mode real --mode camel --workflow pipeline \
  --input <input-otel-del-caso.json> --backends <profilo-reale-del-caso.json> \
  --output <directory-nuova>
```

Sono segnaposto espliciti, non file gia preparati. Non usare `--mode fixtures`
insieme a `--backend-mode real`. Il runner storico `thesis_agents.demo` e il suo
audit sono specifici delle demo mock e non certificano la nuova matrice reale.

Conservare per run: comando, input, profilo senza segreti, hash e manifest delle
fonti, build/JAR/SBOM/OTel, snapshot CTI, candidate, checkpoint nativi quando
applicabili, spiegazioni, record finale/ricevuta/rilettura e tempi delle fasi.
Nei casi senza candidate, `assessment_completed` e fasi native skipped sono un
esito completo atteso; non inventare una ricevuta di finalizzazione.

Controllo offline della preparazione corrente:
[report](../../output/controlled-cases-20261105/report.md).
