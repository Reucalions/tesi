# Chaincode dedicato alla provenienza della tesi

Implementazione additiva di `StoreProvenance(runID, documentJSON)` e
`GetProvenance(runID)`. Non modifica i chaincode BWAF/Tiny-ME. Dipendenze Fabric
fissate alle versioni della baseline, con `go.sum` incluso.

Con Go 1.25.4:

```sh
go test ./...
go build -o /tmp/thesis-provenance .
```

I test usano lo stub Fabric, non una rete o un ledger effettivi. Compilazione,
test e schema delle risposte sono stati verificati. Non è ancora verificata
l'installazione del chaincode su Fablo.

Dalla radice di `tesi`, quando Docker è attivo:

```sh
docker build -t thesis-provenance:0.1 services/provenance_chaincode
```

L'immagine è predisposta ma non è stata costruita in questa sessione.
Installare il chaincode sul canale con nome `thesis-provenance`. Per un
deployment tradizionale il programma usa `contractapi.Start`; per un servizio
esterno supporta `shim.ChaincodeServer`, come previsto dalla
[documentazione Fabric 2.5](https://hyperledger-fabric.readthedocs.io/en/release-2.5/cc_service.html).

Per la modalità servizio esterno occorrono:

- `CHAINCODE_SERVER_ADDRESS`: indirizzo di ascolto del servizio;
- `CORE_CHAINCODE_ID_NAME`: ID esatto del pacchetto installato sul peer;
- `CHAINCODE_TLS_KEY_FILE` e `CHAINCODE_TLS_CERT_FILE`: file TLS del server;
- oppure `CHAINCODE_TLS_DISABLED=true` per il laboratorio locale configurato
  esplicitamente senza TLS fra peer e chaincode.

Packaging, endpoint in `connection.json`, approvazione e commit della
definizione devono corrispondere alla rete scelta. Il Dockerfile da solo non
installa il contratto e non sostituisce questi passaggi. Non sono stati
modificati `fablo-config.json`, reti o immagini delle baseline.

Il chaincode salva una stringa JSON canonica e ne calcola l'hash sui byte
UTF-8. Il gateway invia JSON compatto, chiavi ordinate e Unicode non escapato.
La busta della risposta Fabric può escapare caratteri senza alterare la
stringa memorizzata. Il digest riguarda il documento ricevuto, non il JSON
esterno che racchiude la risposta.

Una seconda scrittura identica conserva l'ID della prima transazione; un
documento diverso sullo stesso run viene respinto. Le scritture concorrenti
sono soggette ai controlli MVCC di Fabric. Il client non effettua retry
automatici di transazioni dall'esito incerto.

Configurazione gateway, limiti e collaudo:
[integrazione nativa](../../docs/archivio/fabric-native-integration.md).
