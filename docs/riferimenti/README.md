# Registro delle fonti

Per la derivazione della formula e le attribuzioni, leggi [fonti e scelte](../fonti-e-scelte.md).
I riferimenti sono identificati con gli stessi codici usati nella relazione.

`fonti.json` è il registro principale. Dopo una modifica, esegui dalla radice:

```bash
python3 docs/riferimenti/aggiorna_fonti.py
/tmp/tesi-materiali-venv/bin/python docs/materiali/genera_materiali.py
```

Il primo comando aggiorna questo catalogo, il BibTeX e la bibliografia Markdown;
il secondo rigenera i materiali. Non vengono effettuate inferenze o chiamate di rete.

## [TESI] Toward Explainable Agentic Cyber Threat Intelligence: Semantic Smart Contracts, Argumentation Ranking and Runtime Observability

**[TESI]** Alessandro Costa. *Toward Explainable Agentic Cyber Threat Intelligence: Semantic Smart Contracts, Argumentation Ranking and Runtime Observability*. 2026.

Fonte: proposta-agentic-cti.pdf

**Ambito:** Documento progettuale fornito dall’autore; sezioni 2, 4–9, 11–12, 15–17. Definisce architettura e baseline previste, non la formula numerica del mock.

**Consultazione:** 2026-09-17; documento fornito o fonte dei materiali grafici; ricontrollato.

SHA-256 della copia: `9eed32a42b3dd3655e725c393306cdea8b5426d434a609d0434faf701cabf5bf`.

## [CAMEL] CAMEL: Communicative Agents for "Mind" Exploration of Large Language Model Society

**[CAMEL]** Guohao Li and Hasan Abed Al Kader Hammoud and Hani Itani and Dmitrii Khizbullin and Bernard Ghanem. *CAMEL: Communicative Agents for "Mind" Exploration of Large Language Model Society*. 2023.

Fonte: https://arxiv.org/abs/2303.17760

**Ambito:** Consultati abstract e metadati per il riferimento al framework di agenti comunicanti. Non giustifica il DAG specifico né gli hook Workforce 0.2.90.

**Consultazione:** 2026-09-17; consultato nella revisione bibliografica; non attestazione di uso durante sviluppo.

## [CAMEL-SDK] CAMEL repository, versione v0.2.90

**[CAMEL-SDK]** CAMEL-AI. *CAMEL repository, versione v0.2.90*. s.d..

Fonte: https://github.com/camel-ai/camel/tree/v0.2.90

**Ambito:** Repository/versione e documentazione Workforce; API e comportamento della configurazione sono verificabili nel codice locale installato e nei test del progetto. Non attribuire al paper 2023 le API attuali.

**Consultazione:** 2026-09-17; consultato nella revisione bibliografica; non attestazione di uso durante sviluppo.

## [PYDANTIC] Models — Pydantic documentation

**[PYDANTIC]** Pydantic contributors. *Models — Pydantic documentation*. s.d..

Fonte: https://docs.pydantic.dev/latest/concepts/models/

**Ambito:** Metodi di validazione e serializzazione, copie e tipi. Le pagine latest sono consultate in questa revisione; versione del progetto 2.12.0. I vincoli tra artefatti sono codice originale del progetto.

**Consultazione:** 2026-09-17; consultato nella revisione bibliografica; non attestazione di uso durante sviluppo.

## [OLLAMA-API] OpenAI compatibility

**[OLLAMA-API]** Ollama. *OpenAI compatibility*. s.d..

Fonte: https://docs.ollama.com/api/openai-compatibility

**Ambito:** Sezione Local server usage: endpoint locale compatibile e uso del client. Non implica una chiamata al cloud OpenAI.

**Consultazione:** 2026-09-17; consultato nella revisione bibliografica; non attestazione di uso durante sviluppo.

## [OLLAMA-MODELFILE] Modelfile Reference

**[OLLAMA-MODELFILE]** Ollama. *Modelfile Reference*. s.d..

Fonte: https://docs.ollama.com/modelfile

**Ambito:** Significato di FROM, num_ctx e temperature. La scelta 16384/0 è una configurazione del progetto, non un risultato consigliato dal paper CAMEL.

**Consultazione:** 2026-09-17; consultato nella revisione bibliografica; non attestazione di uso durante sviluppo.

## [QWEN] qwen3:4b-instruct — model library entry

**[QWEN]** Ollama. *qwen3:4b-instruct — model library entry*. s.d..

Fonte: https://ollama.com/library/qwen3:4b-instruct

**Ambito:** Tag distribuito da Ollama, parametri e quantizzazione. Per i pesi effettivamente provati fa fede il digest nel manifest locale; il tag remoto può cambiare.

**Consultazione:** 2026-09-17; consultato nella revisione bibliografica; non attestazione di uso durante sviluppo.

## [LOG4J] Apache Logging Services — Security, CVE-2021-44228

**[LOG4J]** Apache Software Foundation. *Apache Logging Services — Security, CVE-2021-44228*. s.d..

Fonte: https://logging.apache.org/security.html

**Ambito:** Riferimento esterno per la vulnerabilità Log4j. L’evidenza runtime payment-api, i vincoli e il lookup esatto restano dati dimostrativi; non sono rilevamenti reali.

**Consultazione:** 2026-09-17; consultato nella revisione bibliografica; non attestazione di uso durante sviluppo.

## [BWAF-MN] Modular Semantics and Characteristics for Bipolar Weighted Argumentation Graphs

**[BWAF-MN]** Till Mossakowski and Fabian Neuhaus. *Modular Semantics and Characteristics for Bipolar Weighted Argumentation Graphs*. 2018.

Fonte: https://arxiv.org/abs/1807.06685

**Ambito:** Consultati abstract/metadati: distinzione aggregazione/influenza e pluralità delle semantiche. Riferimento teorico aggiunto ora, non fonte dei coefficienti 0.5.

**Consultazione:** 2026-09-17; consultato nella revisione bibliografica; non attestazione di uso durante sviluppo.

## [BWAF-P] Extending Modular Semantics for Bipolar Weighted Argumentation

**[BWAF-P]** Nico Potyka. *Extending Modular Semantics for Bipolar Weighted Argumentation*. 2019.

Fonte: https://www.ifaamas.org/Proceedings/aamas2019/pdfs/p1722.pdf

**Ambito:** AAMAS 2019, pp. 1722–1730; consultati introduzione e definizioni dei grafi e delle semantiche modulari. Non viene implementata né riprodotta una sua semantica nel mock.

**Consultazione:** 2026-09-17; consultato nella revisione bibliografica; non attestazione di uso durante sviluppo.

## [TINYME] A multiplatform reasoning engine for the Semantic Web of Everything

**[TINYME]** Michele Ruta and Floriano Scioscia and Ivano Bilenchi and Filippo Gramegna and Giuseppe Loseto and Saverio Ieva and Agnese Pinto. *A multiplatform reasoning engine for the Semantic Web of Everything*. 2022.

Fonte: https://sisinflab.poliba.it/publications/2022/RSBGLIP22/Ruta_et_al_JWS2022_Tiny-ME_CR.pdf

**Ambito:** Journal of Web Semantics 73, 100709. Consultati abstract e introduzione della versione autore: motore di matchmaking e ragionamento OWL. Non documenta il chaincode privato della tesi.

**Consultazione:** 2026-09-17; consultato nella revisione bibliografica; non attestazione di uso durante sviluppo.

## [PROVO] PROV-O: The PROV Ontology

**[PROVO]** W3C. *PROV-O: The PROV Ontology*. 2013.

Fonte: https://www.w3.org/TR/prov-o/

**Ambito:** Entità, attività e agenti come riferimento concettuale. JSON e hash del mock non dimostrano conformità PROV-O.

**Consultazione:** 2026-09-17; consultato nella revisione bibliografica; non attestazione di uso durante sviluppo.

## [OTEL] What is OpenTelemetry?

**[OTEL]** OpenTelemetry. *What is OpenTelemetry?*. s.d..

Fonte: https://opentelemetry.io/docs/what-is-opentelemetry/

**Ambito:** Definizione e segnali di telemetria per l’integrazione futura; non è attualmente un produttore di input nel prototipo.

**Consultazione:** 2026-09-17; consultato nella revisione bibliografica; non attestazione di uso durante sviluppo.

## [MCP] Architecture — specification 2025-06-18

**[MCP]** Model Context Protocol contributors. *Architecture — specification 2025-06-18*. 2025.

Fonte: https://modelcontextprotocol.io/specification/2025-06-18/architecture

**Ambito:** Architettura del protocollo, riferimento per il futuro trasporto dei tool. Non prova che il mock usi MCP.

**Consultazione:** 2026-09-17; consultato nella revisione bibliografica; non attestazione di uso durante sviluppo.

## [OSV] Open Source Vulnerability format

**[OSV]** OpenSSF. *Open Source Vulnerability format*. s.d..

Fonte: https://ossf.github.io/osv-schema/

**Ambito:** Schema delle vulnerabilità e versioni interessate; futuro adapter, non fonte live del lookup attuale.

**Consultazione:** 2026-09-17; consultato nella revisione bibliografica; non attestazione di uso durante sviluppo.

## [OWL] OWL 2 Web Ontology Language Document Overview, Second Edition

**[OWL]** W3C. *OWL 2 Web Ontology Language Document Overview, Second Edition*. 2012.

Fonte: https://www.w3.org/TR/owl2-overview/

**Ambito:** Standard del linguaggio ontologico; non identifica la specifica ontologia OWL CTI dei repository privati.

**Consultazione:** 2026-09-17; consultato nella revisione bibliografica; non attestazione di uso durante sviluppo.

## [FABRIC] Smart Contracts and Chaincode

**[FABRIC]** Hyperledger Fabric contributors. *Smart Contracts and Chaincode*. s.d..

Fonte: https://hyperledger-fabric.readthedocs.io/en/latest/smartcontract/smartcontract.html

**Ambito:** Ruolo di smart contract e chaincode; riferimento generale dell’integrazione prevista, non verifica della rete privata.

**Consultazione:** 2026-09-17; consultato nella revisione bibliografica; non attestazione di uso durante sviluppo.

## [SBOM] Framing Software Component Transparency: Establishing a Common Software Bill of Materials, Third Edition

**[SBOM]** CISA. *Framing Software Component Transparency: Establishing a Common Software Bill of Materials, Third Edition*. 2024.

Fonte: https://www.cisa.gov/sites/default/files/2024-10/SBOM%20Framing%20Software%20Component%20Transparency%202024.pdf

**Ambito:** Sezione 2 consultata per la definizione di SBOM; non è un dataset già ingerito dal mock.

**Consultazione:** 2026-09-17; consultato nella revisione bibliografica; non attestazione di uso durante sviluppo.

## [POLIBA] Piano della comunicazione 2022

**[POLIBA]** Politecnico di Bari. *Piano della comunicazione 2022*. 2022.

Fonte: https://www.poliba.it/sites/default/files/piano_comunicazione_2022_3_aprile_2022.pdf

**Ambito:** Sezione Il Marchio completo, p. 46: PT Sans come base del logotipo e ottanio #008195. Estratto indicizzato consultato; il download tramite browser non è riuscito. Non è un template obbligatorio di tesi.

**Consultazione:** 2026-09-17; documento fornito o fonte dei materiali grafici; ricontrollato.

## [PT-SANS] PT Sans — Google Fonts distribution

**[PT-SANS]** ParaType and Google Fonts. *PT Sans — Google Fonts distribution*. s.d..

Fonte: https://github.com/google/fonts/tree/main/ofl/ptsans

**Ambito:** File dei font e SIL OFL scaricati; licenza e hash sono in docs/materiali/fonts/. Il logo è un asset separato da https://www.poliba.it/sites/default/files/logo_poliba_orizzontale_ufficiale.png.

**Consultazione:** 2026-09-17; documento fornito o fonte dei materiali grafici; ricontrollato.

## [BASE-PIPELINE] agent-based-cti-argumentation-pipeline

**[BASE-PIPELINE]** sisinflab-swot (organizzazione del repository; autori individuali da confermare). *agent-based-cti-argumentation-pipeline*. s.d..

Fonte: https://github.com/sisinflab-swot/agent-based-cti-argumentation-pipeline/tree/c2ea54278bc5f44730693cdf7f86fc3584e54f70

**Ambito:** Repository privato; copia locale letta nella revisione bibliografica. Commit c2ea54278bc5f44730693cdf7f86fc3584e54f70. Non eseguito né integrato nel mockup. File e hash in baseline-locali.json.

**Consultazione:** 2026-09-17; consultato ora in sola lettura; non fonte originaria attestata della formula mock.

## [BASE-LEDGER] semantic-cti-ledger-argumentation

**[BASE-LEDGER]** sisinflab-swot (organizzazione del repository; autori individuali da confermare). *semantic-cti-ledger-argumentation*. s.d..

Fonte: https://github.com/sisinflab-swot/semantic-cti-ledger-argumentation/tree/a3dab4a5def79dda356dd753aa34306e03ea346a

**Ambito:** Repository privato; copia locale letta nella revisione bibliografica. Commit a3dab4a5def79dda356dd753aa34306e03ea346a. Non eseguito né integrato nel mockup. File e hash in baseline-locali.json.

**Consultazione:** 2026-09-17; consultato ora in sola lettura; non fonte originaria attestata della formula mock.
