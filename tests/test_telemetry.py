"""Acquisizione OTEL: fixture dichiarate, parser esterno e confine HTTP effettivo."""

import hashlib
import importlib.util
import json
import socket
import subprocess
import sys
import time
from datetime import timedelta
from pathlib import Path

import httpx
import pytest

from thesis_agents.backends import BackendSettings, connect_backends
from thesis_agents.mcp.client import digest
from thesis_agents.orchestration.artifacts import ArtifactSession
from thesis_agents.orchestration.workforce import run_camel
from thesis_agents.schemas import ProvenanceRecord, RuntimeEvidence, VulnerabilityReport
from thesis_agents.schemas.telemetry_source import TelemetryInput, TelemetryQuery, unix_nano
from thesis_agents.telemetry.settings import TelemetryHTTPSettings
from thesis_agents.tools.telemetry_http import HTTPTelemetryTool, evidence_from_snapshot

SERVER = Path(__file__).resolve().parents[1] / "services/otel_gateway/server.py"


@pytest.fixture
def gateway():
    spec = importlib.util.spec_from_file_location("gateway_under_test", SERVER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def telemetry_input(case):
    return TelemetryInput(
        service_name="test-service",
        service_instance_id="test-instance",
        package_name="log4j-core",
        start_time="2026-01-01T00:00:00Z",
        end_time="2026-01-01T00:01:00Z",
        available_capabilities=case.available_capabilities,
    )


def otel_document(case, *, version="2.14.1"):
    attrs = {
        "service.name": case.service_name,
        "service.instance.id": case.service_instance_id,
        "thesis.software.name": case.package_name,
        "thesis.software.version": version,
    }
    return {
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
                            {
                                "observedTimeUnixNano": str(unix_nano(case.start_time) + 1000),
                                "body": {
                                    "stringValue": "Synthetic observation for transport tests"
                                },
                            }
                        ]
                    }
                ],
            }
        ]
    }


def write_export(path, *documents):
    path.write_text("".join(json.dumps(d) + "\n" for d in documents))
    return path


@pytest.fixture
def export(tmp_path, telemetry_input):
    return write_export(tmp_path / "otel.json", otel_document(telemetry_input))


def snapshot(gateway, export, case):
    return gateway.read_snapshot(
        export, case.query(), source_id="test-export", acquisition="recorded"
    )


def test_runtime_identity_unknown_flags_and_provenance(gateway, export, telemetry_input):
    data = snapshot(gateway, export, telemetry_input)
    evidence = evidence_from_snapshot(data)
    assert evidence.software[0].version == "2.14.1"
    assert evidence.endpoint_exposed is None and evidence.deserialization_observed is None
    assert data.source_sha256 == hashlib.sha256(export.read_bytes()).hexdigest()
    assert evidence.telemetry.snapshot_sha256 == digest(data.model_dump(mode="json"))
    assert evidence.software[0].evidence_id == data.observations[0].evidence_id
    assert data.observations[0].pointer == "/resourceLogs/0/scopeLogs/0/logRecords/0"
    assert data.acquisition == "recorded"
    assert data.observations[0].observed_time_unix_nano < unix_nano(data.acquired_at)


@pytest.mark.parametrize("mismatch", ["instance", "window", "package"])
def test_query_filters_do_not_mix_assets_or_windows(gateway, export, telemetry_input, mismatch):
    if mismatch == "instance":
        telemetry_input.service_instance_id = "another-instance"
    elif mismatch == "package":
        telemetry_input.package_name = "another-package"
    else:
        values = telemetry_input.model_dump()
        values["end_time"] += timedelta(days=1)
        values["start_time"] += timedelta(days=1)
        telemetry_input = TelemetryInput.model_validate(values)
    data = snapshot(gateway, export, telemetry_input)
    assert data.observations == []
    with pytest.raises(ValueError, match="No supported observations"):
        evidence_from_snapshot(data)


def test_collector_self_log_is_distinct_from_yaml_and_other_runtime(gateway, tmp_path):
    case = TelemetryInput(
        service_name="otelcol-contrib",
        service_instance_id="collector-123",
        package_name="otelcol-contrib",
        start_time="2026-01-01T00:00:00Z",
        end_time="2026-01-01T00:01:00Z",
    )
    metadata = {
        "resource": {
            "service.name": "otelcol-contrib",
            "service.version": "0.148.0",
            "service.instance.id": "collector-123",
        },
        "otelcol.component.id": "filelog/docker",
        "otelcol.signal": "logs",
    }
    records = [
        {
            "observedTimeUnixNano": str(unix_nano(case.start_time) + 10),
            "body": {"stringValue": body},
        }
        for body in ("image: log4j:2.14.1", "payment-api started", "info\t" + json.dumps(metadata))
    ]
    path = write_export(
        tmp_path / "mixed.json",
        {"resourceLogs": [{"resource": {}, "scopeLogs": [{"logRecords": records}]}]},
    )
    data = snapshot(gateway, path, case)
    assert (data.file_record_count, data.recognized_record_count, len(data.observations)) == (
        3,
        1,
        1,
    )
    assert evidence_from_snapshot(data).software[0].package == "otelcol-contrib"


def test_ambiguous_versions_are_not_silently_selected(gateway, export, telemetry_input):
    write_export(
        export, otel_document(telemetry_input), otel_document(telemetry_input, version="9.0")
    )
    data = snapshot(gateway, export, telemetry_input)
    with pytest.raises(ValueError, match="Multiple observed versions"):
        evidence_from_snapshot(data)


def test_missing_or_untrusted_flags_never_turn_into_false(gateway, export, telemetry_input):
    doc = otel_document(telemetry_input)
    doc["resourceLogs"][0]["resource"]["attributes"].append(
        {"key": "thesis.endpoint.exposed", "value": {"stringValue": "false"}}
    )
    write_export(export, doc)
    with pytest.raises(ValueError):
        snapshot(gateway, export, telemetry_input)


def test_invalid_window_and_partial_export_are_rejected(gateway, export, telemetry_input):
    with pytest.raises(ValueError, match="window"):
        TelemetryQuery.model_validate(
            telemetry_input.query().model_dump() | {"end_time": telemetry_input.start_time}
        )
    export.write_text('{"resourceLogs":')
    with pytest.raises(ValueError):
        snapshot(gateway, export, telemetry_input)


def test_rotated_export_is_rejected(gateway, export, telemetry_input, monkeypatch):
    original_fstat = gateway.os.fstat
    calls = 0

    def rotate_during_read(fd):
        nonlocal calls
        calls += 1
        if calls == 2:
            replacement = export.with_suffix(".replacement")
            replacement.write_bytes(export.read_bytes())
            replacement.replace(export)
        return original_fstat(fd)

    monkeypatch.setattr(gateway.os, "fstat", rotate_during_read)
    with pytest.raises(ValueError, match="changed while reading"):
        snapshot(gateway, export, telemetry_input)


def test_remote_evidence_cannot_be_published_before_acquisition_or_edited(
    gateway, export, telemetry_input, tmp_path
):
    data = snapshot(gateway, export, telemetry_input)

    class Source:
        def collect(self, query):
            return data

    session = ArtifactSession(
        telemetry_input, tmp_path / "run", mode="camel", telemetry_tool=Source()
    )
    evidence = evidence_from_snapshot(data)
    with pytest.raises(ValueError, match="collect_runtime_evidence"):
        session.publish_runtime_evidence(evidence.model_dump_json())
    expected = session.collect_runtime_evidence()
    assert session.collect_runtime_evidence() == expected
    edited = evidence.model_copy(deep=True)
    edited.endpoint_exposed = False
    with pytest.raises(ValueError, match="exact evidence"):
        session.publish_runtime_evidence(edited.model_dump_json())
    session.publish_runtime_evidence(evidence.model_dump_json())
    saved = session.output_dir / "telemetry_snapshot.json"
    payload = json.loads(saved.read_text())
    payload["source_id"] = "altered"
    saved.write_text(json.dumps(payload))
    with pytest.raises(ValueError, match="snapshot"):
        session.lookup_vulnerabilities()


def test_otel_publication_schema_requires_exact_source(gateway, export, telemetry_input, tmp_path):
    from thesis_agents.orchestration.publication_tools import PublicationTools

    data = snapshot(gateway, export, telemetry_input)

    class Source:
        def collect(self, query):
            return data

    session = ArtifactSession(telemetry_input, tmp_path / "run", telemetry_tool=Source())
    tool = PublicationTools(session).resolve("publish_runtime_evidence")
    payload_schema = tool.get_openai_tool_schema()["function"]["parameters"]["properties"][
        "payload"
    ]
    assert "telemetry" in payload_schema["required"]
    assert "telemetry" in session.get_context()["schemas"]["runtime_evidence"]["required"]
    evidence = evidence_from_snapshot(data).model_dump(mode="json")
    with pytest.raises(ValueError, match="collect_runtime_evidence"):
        tool(payload=evidence)
    expected = session.collect_runtime_evidence()
    for malformed in (
        {**evidence, "telemetry": None},
        {k: v for k, v in evidence.items() if k != "telemetry"},
        {**evidence, "telemetry": {**evidence["telemetry"], "source_sha256": "0" * 64}},
    ):
        with pytest.raises(ValueError):
            tool(payload=malformed)
        assert not (session.output_dir / "runtime_evidence.json").exists()
    assert tool(payload=expected) == expected


@pytest.fixture
def gateway_url(export, tmp_path):
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        base = f"http://127.0.0.1:{listener.getsockname()[1]}"
        with (tmp_path / "gateway.log").open("w+") as log:
            process = subprocess.Popen(
                [
                    sys.executable,
                    str(SERVER),
                    "--file",
                    str(export),
                    "--source-id",
                    "test-export",
                    "--fd",
                    str(listener.fileno()),
                ],
                pass_fds=(listener.fileno(),),
                stdout=log,
                stderr=log,
            )
            try:
                with httpx.Client(timeout=0.2, trust_env=False) as http:
                    for _ in range(150):
                        if process.poll() is not None:
                            log.seek(0)
                            pytest.fail(log.read())
                        try:
                            if http.get(base + "/health").status_code == 200:
                                break
                        except httpx.HTTPError:
                            pass
                        time.sleep(0.02)
                    else:
                        pytest.fail("Telemetry gateway not ready")
                yield base + "/v1/observations"
            finally:
                process.terminate()
                process.wait(timeout=5)


@pytest.mark.mcp_http
def test_http_camel_four_agents_preserve_observations(gateway_url, telemetry_input, tmp_path):
    from test_camel_integration import ScriptedToolModel

    settings = BackendSettings(
        telemetry={
            "transport": "http",
            "url": gateway_url,
            "source_id": "test-export",
            "acquisition": "recorded",
        }
    )
    session = ArtifactSession(
        telemetry_input, tmp_path / "run", mode="camel", model="scripted-test-only"
    )
    model = ScriptedToolModel(session)
    with connect_backends(session, settings):
        result = run_camel(session, lambda: model)
    assert session.assert_complete() == result
    assert result.status == "selected"  # Lookup Log4j e strategie sono fixture del test.
    assert model.tool_calls.count("collect_runtime_evidence") == 1
    context = model.received_contexts["strategic"]
    assert context["artifacts"]["runtime_evidence"]["endpoint_exposed"] is None
    for name in ("runtime_evidence", "vulnerability_report", "candidate_strategies"):
        assert context["artifacts"][name] == json.loads(
            (session.output_dir / f"{name}.json").read_text()
        )
    assert context["artifact_producers"]["runtime_evidence"] == "TelemetryAgent"
    evidence = session.require("runtime_evidence", RuntimeEvidence)
    report = session.require("vulnerability_report", VulnerabilityReport)
    assert report.vulnerabilities[0].evidence_ids == [evidence.software[0].evidence_id]
    provenance = session.require("provenance", ProvenanceRecord)
    assert "telemetry_snapshot" in {e.id for e in provenance.entities}
    assert (
        "telemetry_snapshot" in next(a for a in provenance.activities if a.id == "telemetry").used
    )
    assert "acquisition=recorded" in result.explanation


@pytest.mark.mcp_http
@pytest.mark.parametrize("fault", ["source", "acquisition", "empty", "malformed", "nested"])
def test_http_failures_never_fall_back_to_static(
    gateway_url, telemetry_input, export, tmp_path, fault
):
    settings = TelemetryHTTPSettings(
        url=gateway_url,
        source_id="wrong-source" if fault == "source" else "test-export",
        acquisition="collector-file" if fault == "acquisition" else "recorded",
    )
    if fault == "empty":
        telemetry_input.service_instance_id = "no-such-instance"
    elif fault == "malformed":
        export.write_text("not-json")
    elif fault == "nested":
        export.write_text('{"resourceLogs": [null]}')
    events = []
    session = ArtifactSession(
        telemetry_input,
        tmp_path / "run",
        mode="camel",
        telemetry_tool=HTTPTelemetryTool(settings, events.append),
    )
    with pytest.raises((ValueError, RuntimeError)):
        session.collect_runtime_evidence()
    assert not (session.output_dir / "runtime_evidence.json").exists()
    assert events[0]["status"] == ("validated" if fault == "empty" else "failed")
