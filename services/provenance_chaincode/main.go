// Chaincode PROV-O separato: nessuna modifica ai contratti delle baseline.
package main

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"fmt"
	"os"
	"regexp"

	"github.com/hyperledger/fabric-chaincode-go/shim"
	"github.com/hyperledger/fabric-contract-api-go/contractapi"
)

type Contract struct{ contractapi.Contract }

type StoredProvenance struct {
	RunID          string `json:"run_id"`
	DocumentJSON   string `json:"document_json"`
	DocumentSHA256 string `json:"document_sha256"`
	TxID           string `json:"tx_id"`
}

var runPattern = regexp.MustCompile(`^[A-Za-z0-9_.:-]+$`)

func key(runID string) (string, error) {
	if !runPattern.MatchString(runID) {
		return "", fmt.Errorf("invalid run ID")
	}
	return "prov:" + runID, nil
}

func (c *Contract) StoreProvenance(ctx contractapi.TransactionContextInterface, runID, document string) (*StoredProvenance, error) {
	stateKey, err := key(runID)
	if err != nil {
		return nil, err
	}
	if len(document) > 4_000_000 {
		return nil, fmt.Errorf("provenance document too large")
	}
	var parsed struct {
		Record struct {
			RunID string `json:"run_id"`
		} `json:"record"`
		JSONLD map[string]interface{} `json:"jsonld"`
	}
	if err := json.Unmarshal([]byte(document), &parsed); err != nil {
		return nil, err
	}
	if parsed.Record.RunID != runID || parsed.JSONLD["@type"] != "prov:Bundle" {
		return nil, fmt.Errorf("inconsistent provenance run or bundle")
	}
	hash := sha256.Sum256([]byte(document))
	digest := hex.EncodeToString(hash[:])
	existing, err := ctx.GetStub().GetState(stateKey)
	if err != nil {
		return nil, err
	}
	if existing != nil {
		var stored StoredProvenance
		if err := json.Unmarshal(existing, &stored); err != nil {
			return nil, err
		}
		if stored.DocumentSHA256 != digest {
			return nil, fmt.Errorf("provenance is immutable")
		}
		return &stored, nil
	}
	stored := &StoredProvenance{runID, document, digest, ctx.GetStub().GetTxID()}
	data, err := json.Marshal(stored)
	if err != nil {
		return nil, err
	}
	if err := ctx.GetStub().PutState(stateKey, data); err != nil {
		return nil, err
	}
	return stored, nil
}

func (c *Contract) GetProvenance(ctx contractapi.TransactionContextInterface, runID string) (*StoredProvenance, error) {
	stateKey, err := key(runID)
	if err != nil {
		return nil, err
	}
	data, err := ctx.GetStub().GetState(stateKey)
	if err != nil {
		return nil, err
	}
	if data == nil {
		return nil, fmt.Errorf("provenance not found")
	}
	var stored StoredProvenance
	if err := json.Unmarshal(data, &stored); err != nil {
		return nil, err
	}
	return &stored, nil
}

func main() {
	cc, err := contractapi.NewChaincode(&Contract{})
	if err != nil {
		panic(err)
	}
	if address := os.Getenv("CHAINCODE_SERVER_ADDRESS"); address != "" {
		tls := shim.TLSProperties{Disabled: os.Getenv("CHAINCODE_TLS_DISABLED") == "true"}
		if !tls.Disabled {
			tls.Key, err = os.ReadFile(os.Getenv("CHAINCODE_TLS_KEY_FILE"))
			if err != nil {
				panic(err)
			}
			tls.Cert, err = os.ReadFile(os.Getenv("CHAINCODE_TLS_CERT_FILE"))
			if err != nil {
				panic(err)
			}
		}
		server := &shim.ChaincodeServer{
			CCID: os.Getenv("CORE_CHAINCODE_ID_NAME"), Address: address, CC: cc, TLSProps: tls,
		}
		if err := server.Start(); err != nil {
			panic(err)
		}
		return
	}
	if err := cc.Start(); err != nil {
		panic(err)
	}
}
