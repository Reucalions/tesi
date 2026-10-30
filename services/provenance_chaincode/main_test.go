package main

import (
	"encoding/json"
	"strings"
	"testing"

	"github.com/hyperledger/fabric-chaincode-go/shimtest"
	"github.com/hyperledger/fabric-contract-api-go/contractapi"
)

func TestProvenanceLifecycle(t *testing.T) {
	cc, err := contractapi.NewChaincode(&Contract{})
	if err != nil {
		t.Fatal(err)
	}
	stub := shimtest.NewMockStub("provenance", cc)
	doc := `{"jsonld":{"@type":"prov:Bundle","note":"Δ<&>"},"record":{"run_id":"test-run"}}`
	invoke := func(tx string, args ...string) []byte {
		bytes := make([][]byte, len(args))
		for i, arg := range args {
			bytes[i] = []byte(arg)
		}
		response := stub.MockInvoke(tx, bytes)
		if response.Status != 200 {
			t.Fatalf("%s: %s", tx, response.Message)
		}
		return response.Payload
	}
	first := invoke("store-tx", "StoreProvenance", "test-run", doc)
	read := invoke("read-tx", "GetProvenance", "test-run")
	if string(first) != string(read) {
		t.Fatal("stored and retrieved provenance differ")
	}
	var value StoredProvenance
	if err := json.Unmarshal(read, &value); err != nil {
		t.Fatal(err)
	}
	if value.TxID != "store-tx" {
		t.Fatal("transaction ID was not preserved")
	}
	if value.DocumentJSON != doc {
		t.Fatal("canonical Unicode document bytes were not preserved")
	}
	repeated := invoke("retry-tx", "StoreProvenance", "test-run", doc)
	if string(repeated) != string(first) {
		t.Fatal("idempotent retry changed the record")
	}
	conflict := strings.Replace(doc, `"prov:Bundle"`, `"prov:Bundle","changed":true`, 1)
	response := stub.MockInvoke("conflict", [][]byte{[]byte("StoreProvenance"), []byte("test-run"), []byte(conflict)})
	if response.Status == 200 || !strings.Contains(response.Message, "immutable") {
		t.Fatal("conflicting provenance was accepted")
	}
}

func TestProvenanceRejectsWrongRunAndMissingRecord(t *testing.T) {
	cc, err := contractapi.NewChaincode(&Contract{})
	if err != nil {
		t.Fatal(err)
	}
	stub := shimtest.NewMockStub("provenance", cc)
	for _, args := range [][][]byte{
		{[]byte("StoreProvenance"), []byte("run"), []byte(`{"record":{"run_id":"other"},"jsonld":{"@type":"prov:Bundle"}}`)},
		{[]byte("GetProvenance"), []byte("missing")},
		{[]byte("GetProvenance"), []byte("bad/key")},
	} {
		if response := stub.MockInvoke("reject", args); response.Status == 200 {
			t.Fatal("invalid or missing provenance was accepted")
		}
	}
}
