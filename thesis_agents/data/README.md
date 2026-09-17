# Il caso statico `log4j_case.json`

Questa directory contiene l'ingresso dimostrativo del prototipo. Il JSON resta privo di commenti perché il formato non li ammette: questa guida ne spiega i campi senza aggiungere chiavi estranee al contratto Pydantic.

I quattro input `demo_*.json` preparano il caso nominale, l'assenza di una finestra
di manutenzione, il divieto di tutte le azioni e un lookup non supportato.
La [guida agli scenari](../../docs/demo-scenarios.md) descrive risultati attesi,
comandi e differenze tra verifica con fixture e inferenza locale reale.

## Campi dell'input

| Campo | Valore dell'esempio | Significato e utilizzo |
|---|---|---|
| `service_name` | `payment-api` | Identifica il servizio osservato. Diventa `RuntimeEvidence.service_name` e `VulnerabilityReport.asset_id`. |
| `package_name` | `log4j-core` | Nome del pacchetto software. TelemetryAgent lo pubblica in `software[].package`; il lookup lo usa insieme alla versione. |
| `package_version` | `2.14.1` | Versione osservata, mantenuta come stringa. Il mock riconosce questa coppia esatta, senza implementare intervalli di versioni. |
| `endpoint_exposed` | `true` | Fatto booleano sull'esposizione del servizio. Deve essere preservato nell'evidenza e può informare la generazione delle strategie. Non cambia da solo il risultato del lookup statico. |
| `deserialization_observed` | `true` | Segnale del caso dimostrativo. Rimane un fatto osservato, non una conferma di exploit. Il mock KG non lo usa come condizione aggiuntiva della corrispondenza. |
| `available_capabilities` | Lista di cinque capacità | Risorse o possibilità operative presenti nel caso. Il validatore confronta questa lista con i requisiti delle azioni proposte. |
| `prohibited_actions` | Lista vuota | Categorie di azione vietate dalla policy del caso. Possono essere vietate anche se tecnicamente realizzabili. |

I campi booleani usano `true` e `false` JSON, senza virgolette. Campi sconosciuti sono rifiutati. Le due liste operative possono essere omesse: il modello assegna liste vuote, che non equivalgono alle capacità presenti nell'esempio.

## Capacità e categorie di azione

| Azione della candidata | Requisiti obbligatori nel mock |
|---|---|
| `upgrade` | `package_upgrade`, `maintenance_window` |
| `isolate` | `network_isolation` |
| `block_deployment` | `deployment_control` |
| `monitor` | `monitoring` |

La candidata può aggiungere nomi in `prerequisites`; il tool li somma a quelli obbligatori. Omettere un prerequisito nella proposta non elimina il requisito imposto dal backend. `constraints`, invece, appartiene alle candidate e contiene note testuali che il mock non interpreta.

## Percorso del dato

1. La CLI legge e valida il JSON come `StaticTelemetry`.
2. `ArtifactSession` ne conserva una copia e scrive `input.json` nella directory del run.
3. TelemetryAgent produce `RuntimeEvidence`, includendo l'osservazione software con un ID di evidenza.
4. Il tool del VulnerabilityAgent usa pacchetto/versione e riporta l'ID di evidenza nei finding.
5. CountermeasureAgent legge evidence e report separatamente e propone strategie.
6. StrategicAgent legge i tre artefatti distinti. Per la validazione, la sessione aggiunge al `DecisionContext` anche capacità e policy dell'input.

Le capacità non vengono incorporate artificialmente nel `VulnerabilityReport`: appartengono al contesto operativo originale. I file di output preservano questi confini, e la provenienza locale collega l'input alle attività che lo usano.

## Variazioni utili per capire il mock

Per provare variazioni, crea un altro JSON e passalo con `--input`, mantenendo il caso originale come riferimento:

```bash
.venv/bin/python main.py --mode fixtures --input percorso/altro_caso.json
```

- Togliendo `maintenance_window`, l'upgrade resta primo nel ranking della fixture ma viene rifiutato dalla validazione; si passa a `S_ISOLATE`.
- Svuotando `available_capabilities`, tutte le quattro strategie della fixture vengono rifiutate: `no_valid_strategy`.
- Inserendo `upgrade` in `prohibited_actions`, il validatore rifiuta l'upgrade anche quando i requisiti sono disponibili.
- Usando una coppia pacchetto/versione diversa, il lookup restituisce `unsupported` e la decisione `insufficient_evidence`. Non si sta dichiarando sicuro quel software.

Questi risultati descrivono la modalità `fixtures`, che usa proposte prefissate. Con CAMEL e un LLM le candidate e le loro stime possono cambiare. In nessuna modalità questi tool applicano modifiche al servizio.
