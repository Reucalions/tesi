"""Client public contracts only: source/backend binding, unknown scope and failure audit."""

import json

import pytest
import test_cti_identity_v2

from thesis_agents.mcp import ubuntu_probe
from thesis_agents.mcp.client import MCPError, digest
from thesis_agents.mcp.settings import MCPSettings
from thesis_agents.mcp.ubuntu_contracts import VERDICTS

apache_files = test_cti_identity_v2.apache_files
request_and_response = test_cti_identity_v2.request_and_response
sample = test_cti_identity_v2.sample
v2_sample = test_cti_identity_v2.v2_sample


@pytest.fixture
def package_sample(v2_sample):
    snapshot, _, identity = v2_sample
    request = ubuntu_probe.request_from_snapshot(snapshot)
    e = request.identity.evidence
    payload = {
        "contract": "ubuntu-package-assessment-v1",
        "backend_kind": "mock",
        "request_sha256": digest(request.model_dump(mode="json")),
        "request": request.model_dump(mode="json"),
        "identity_resolution": identity,
        "source_manifest_sha256": "c" * 64,
        "source_identity_dataset_sha256": "1" * 64,
        "source_identity_rule_sha256": identity["rule_sha256"],
        "sources_prepared_at": "2026-10-17T00:00:00Z",
        "engine_sha256": {"synthetic": "d" * 64},
        "comparator": "synthetic-test-comparator",
        "inventory": {
            "host": e.host,
            "distribution": "Ubuntu",
            "release": "bionic",
            "release_version": "18.04",
            "collected_at": e.facts_collected_at.isoformat(),
            "facts_sha256": e.facts_sha256,
            "source_package": "apache2",
            "packages": [
                {
                    "name": name,
                    "version": e.inventory_version,
                    "arch": "amd64",
                    "origin": "Ubuntu",
                    "manager": "apt",
                }
                for name in ("apache2", "apache2-bin")
            ],
            "packaging_notice": {"url": "https://example.invalid/synthetic", "sha256": "e" * 64},
        },
        "inventory_matches": True,
        "source_scope_matches": True,
        "status": "not_assessed",
        "reason": "Synthetic index has no matching identity",
        "scope": "inventoried-package-retrospective-ubuntu-version-check",
        "runtime_applicability": "not_assessed",
        "historical_runtime_state": "not_established",
        "results": [],
        "counts": dict.fromkeys(VERDICTS, 0),
        "limitations": ["Synthetic only"],
    }
    return snapshot, request, payload


def test_identity_missing_does_not_become_package_safety(package_sample):
    _, request, payload = package_sample
    result = ubuntu_probe.validate_assessment(
        payload, request, "mock", dataset_sha256="1" * 64, sources_sha256="c" * 64
    )
    assert result.status == "not_assessed" and result.results == []
    assert result.runtime_applicability == "not_assessed"


@pytest.mark.parametrize(
    "path,value",
    [
        (("request_sha256",), "0" * 64),
        (("source_manifest_sha256",), "0" * 64),
        (("backend_kind",), "real"),
        (("status",), "assessed"),
        (("inventory_matches",), False),
        (("inventory", "packages", 0, "version"), "2.4.29-wrong"),
        (("source_scope_matches",), False),
        (("counts", "fixed"), 1),
        (("runtime_applicability",), "vulnerable"),
        (("historical_runtime_state",), "established"),
    ],
)
def test_inconsistent_or_unjustified_package_claim_rejected(package_sample, path, value):
    _, request, payload = package_sample
    target = payload
    for key in path[:-1]:
        target = target[key]
    target[path[-1]] = value
    with pytest.raises(ValueError):
        ubuntu_probe.validate_assessment(
            payload, request, "mock", dataset_sha256="1" * 64, sources_sha256="c" * 64
        )


def test_probe_preserves_sources_and_failure_audit(package_sample, monkeypatch, tmp_path):
    snapshot, request, payload = package_sample
    path = tmp_path / "snapshot.json"
    path.write_text(snapshot.model_dump_json())
    fail = False

    class Connection:
        def __init__(self, settings, *, contracts, audit):
            self.audit = audit
            assert "assess_ubuntu_package" in contracts

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def call_tool(self, name, arguments, parse):
            assert arguments == request.model_dump(mode="json")
            self.audit({"event": "synthetic-test"})
            if fail:
                raise MCPError("Synthetic transport failure")
            return parse(payload)

    monkeypatch.setattr(ubuntu_probe, "MCPClient", Connection)
    settings = MCPSettings(url="http://127.0.0.1:8006/mcp", expected_kind="mock")
    out = tmp_path / "probe"
    ubuntu_probe.run_probe(settings, path, out, dataset_sha256="1" * 64, sources_sha256="c" * 64)
    assert (out / "telemetry_snapshot.json").read_bytes() == path.read_bytes()
    assert json.loads((out / "summary.json").read_text())["package_status"] == "not_assessed"
    with pytest.raises(FileExistsError):
        ubuntu_probe.run_probe(
            settings, path, out, dataset_sha256="1" * 64, sources_sha256="c" * 64
        )
    fail = True
    out = tmp_path / "failed"
    with pytest.raises(MCPError):
        ubuntu_probe.run_probe(
            settings, path, out, dataset_sha256="1" * 64, sources_sha256="c" * 64
        )
    assert not (out / "package_assessment.json").exists()
    assert json.loads((out / "summary.json").read_text())["status"] == "failed"
    assert json.loads((out / "audit.json").read_text())
