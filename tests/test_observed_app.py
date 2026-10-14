"""Coerenza delle fonti: test offline, senza richiedere Maven o la JVM alla suite."""

import importlib.util
import json
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from thesis_agents.schemas.supply_chain import MavenComponent


@pytest.fixture
def prepare_module():
    path = Path(__file__).resolve().parents[1] / "examples/observed-app/prepare.py"
    spec = importlib.util.spec_from_file_location("observed_app_prepare", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def sources(tmp_path, prepare_module):
    start = datetime(2026, 10, 1, tzinfo=UTC)
    attrs = {
        "service.name": "observed-test",
        "service.instance.id": "instance-1",
        "thesis.software.name": "Apache Log4j Core",
        "thesis.software.version": "2.26.1",
        "thesis.software.jar.sha256": "a" * 64,
    }
    logs = {
        "resourceLogs": [
            {
                "resource": {
                    "attributes": [
                        {"key": k, "value": {"stringValue": v}} for k, v in attrs.items()
                    ]
                },
                "scopeLogs": [
                    {
                        "logRecords": [
                            {"observedTimeUnixNano": str(prepare_module.unix_nano(start) + 1)}
                        ]
                    }
                ],
            }
        ]
    }
    sbom = {
        "bomFormat": "CycloneDX",
        "specVersion": "1.6",
        "components": [
            {
                "bom-ref": "log4j",
                "group": "org.apache.logging.log4j",
                "name": "log4j-core",
                "version": "2.26.1",
                "purl": "pkg:maven/org.apache.logging.log4j/log4j-core@2.26.1?type=jar",
                "hashes": [{"alg": "SHA-256", "content": "a" * 64}],
            }
        ],
    }
    export, inventory = tmp_path / "otel.jsonl", tmp_path / "bom.json"
    export.write_text(json.dumps(logs) + "\n")
    inventory.write_text(json.dumps(sbom))
    return export, inventory, start, start + timedelta(seconds=1)


def test_same_instance_version_and_jar_hash_are_linked(prepare_module, sources):
    case, binding, manifest = prepare_module.inspect_sources(*sources)
    assert case.package_name == "Apache Log4j Core"
    assert binding.service_name == case.service_name
    assert binding.component_ref == "log4j"
    assert manifest["loaded_jar_sha256"] == "a" * 64
    assert "package_version" not in case.model_dump()  # versione ricavata dalla fonte


@pytest.mark.parametrize("fault", ["jar", "version", "old", "instance", "empty"])
def test_incoherent_or_stale_sources_fail(prepare_module, sources, fault):
    export, inventory, start, end = sources
    doc = json.loads(inventory.read_text())
    logs = json.loads(export.read_text())
    if fault == "jar":
        doc["components"][0]["hashes"][0]["content"] = "b" * 64
    elif fault == "version":
        doc["components"][0]["version"] = "2.25.4"
    elif fault == "old":
        start += timedelta(days=1)
        end += timedelta(days=1)
    elif fault == "instance":
        other = json.loads(json.dumps(logs["resourceLogs"][0]))
        other["resource"]["attributes"][1]["value"]["stringValue"] = "instance-2"
        logs["resourceLogs"].append(other)
    elif fault == "empty":
        logs["resourceLogs"] = []
    export.write_text(json.dumps(logs) + "\n")
    inventory.write_text(json.dumps(doc))
    with pytest.raises(ValueError):
        prepare_module.inspect_sources(export, inventory, start, end)


@pytest.mark.parametrize(
    "qualifier", ["?type=war", "?classifier=tests", "?type=jar&classifier=sources"]
)
def test_other_maven_qualifiers_are_not_silently_removed(qualifier):
    with pytest.raises(ValueError, match="type=jar"):
        MavenComponent(
            bom_ref="lib",
            group="example",
            name="lib",
            version="1.0",
            purl="pkg:maven/example/lib@1.0" + qualifier,
        )
