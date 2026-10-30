"""Public v2 contract: false completeness and fabricated selections are rejected."""

import json

import pytest
import test_cti_identity

from thesis_agents.mcp import identity_probe
from thesis_agents.mcp.settings import MCPSettings

apache_files = test_cti_identity.apache_files
request_and_response = test_cti_identity.request_and_response
sample = test_cti_identity.sample


@pytest.fixture
def v2_sample(sample):
    snapshot, request, payload = sample
    payload = json.loads(json.dumps(payload))
    payload.update(
        contract="cti-identity-resolution-v2",
        rule_id="apache-recorded-identity-v2",
        reviewed_dataset_sha256="1" * 64,
        search={
            "software": payload["normalized_query"],
            "dataset": payload["upstream_assessment"]["dataset"],
            "engine_sha256": payload["upstream_assessment"]["engine_sha256"],
            "search_sha256": "c" * 64,
            "matching": payload["upstream_assessment"]["matching"],
            "coverage": {
                "scope": "baseline-normalized-product-exact-and-token",
                "indexed_identities": 10,
                "candidate_bound": 11,
                "token_bound": 55,
                "generated_candidates": 0,
                "rejected_by_matcher": 0,
                "returned_candidates": 0,
                "complete": True,
                "vector_search": False,
            },
        },
    )
    # JSON round trip removes shared references before tampering tests.
    return snapshot, request, json.loads(json.dumps(payload))


def test_v2_explicitly_preserves_v1_compatibility(v2_sample, sample):
    _, request, payload = v2_sample
    result = identity_probe.validate_identity(payload, request, "mock", "1" * 64, contract="v2")
    assert result.search.coverage.complete and result.status == "no_match"
    with pytest.raises(ValueError):
        identity_probe.validate_identity(payload, request, "mock")
    _, request, old = sample
    assert identity_probe.validate_identity(old, request, "mock").contract.endswith("v1")
    with pytest.raises(ValueError):
        identity_probe.validate_identity(old, request, "mock", contract="v2")


@pytest.mark.parametrize(
    "path,value",
    [
        (("search", "coverage", "complete"), False),
        (("search", "coverage", "token_bound"), 10),
        (("search", "coverage", "candidate_bound"), 10),
        (("search", "coverage", "returned_candidates"), 1),
        (("search", "coverage", "generated_candidates"), 1),
        (("search", "dataset", "sha256"), "0" * 64),
        (("search", "software", "version"), "2.4.30"),
        (("search", "engine_sha256"), {}),
        (("status",), "resolved"),
        (("status",), "ambiguous"),
        (("reviewed_dataset_sha256",), "0" * 64),
        (("package_applicability",), "vulnerable"),
    ],
)
def test_inconsistent_search_or_status_rejected(v2_sample, path, value):
    _, request, payload = v2_sample
    target = payload
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    with pytest.raises(ValueError):
        identity_probe.validate_identity(payload, request, "mock", contract="v2")


def test_probe_uses_v2_schema_and_saves_coverage(v2_sample, tmp_path, monkeypatch):
    snapshot, _, payload = v2_sample
    source = tmp_path / "snapshot.json"
    source.write_text(snapshot.model_dump_json())

    class Connection:
        def __init__(self, settings, *, contracts, audit):
            schema = contracts["resolve_software_identity"][1]
            assert schema["properties"]["contract"]["const"] == "cti-identity-resolution-v2"

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def call_tool(self, name, arguments, parse):
            return parse(payload)

    monkeypatch.setattr(identity_probe, "MCPClient", Connection)
    out = tmp_path / "probe"
    identity_probe.run_probe(
        MCPSettings(url="http://127.0.0.1:8005/mcp", expected_kind="mock"),
        source,
        out,
        contract="v2",
    )
    summary = json.loads((out / "summary.json").read_text())
    assert summary["contract_version"] == "v2"
    assert summary["search_coverage"]["complete"]
    assert summary["candidate_counts"] == {"equivalent": 0, "excluded": 0, "unresolved": 0}
