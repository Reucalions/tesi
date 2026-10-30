"""Fixture sintetiche dichiarate: nessun download o dataset privato richiesto."""

import hashlib
import json
from http.server import ThreadingHTTPServer
from threading import Thread

import pytest

from services.otel_gateway.apache_recorded import prepare_binding
from services.otel_gateway.server import handler_for, read_snapshot
from thesis_agents.orchestration.artifacts import ArtifactSession
from thesis_agents.orchestration.workforce import run_camel
from thesis_agents.schemas import LookupResult, RuntimeEvidence
from thesis_agents.schemas.telemetry_source import TelemetryInput, TelemetrySnapshot
from thesis_agents.telemetry.settings import TelemetryHTTPSettings
from thesis_agents.tools.telemetry_http import HTTPTelemetryTool, evidence_from_snapshot


@pytest.fixture
def apache_files(tmp_path):
    body = (
        "[Mon Jan 24 06:25:18.103330 2022] [mpm_prefork:notice] [pid 29640] "
        "AH00163: Apache/2.4.29 (Ubuntu) OpenSSL/1.1.1 configured -- resuming normal operations"
    )
    members = tmp_path / "members"
    logs = members / "gather/webserver/logs/apache2"
    logs.mkdir(parents=True)
    (logs / "error.log.1").write_text(body + "\n")
    package = [
        {"name": "apache2", "version": "2.4.29-1ubuntu4.21", "origin": "Ubuntu", "source": "apt"}
    ]
    facts = {
        "inventory_hostname": "webserver",
        "ansible_hostname": "webserver",
        "ansible_fqdn": "synthetic.example",
        "ansible_distribution": "Ubuntu",
        "ansible_distribution_version": "18.04",
        "ansible_distribution_release": "bionic",
        "ansible_date_time": {"iso8601": "2022-01-25T06:55:29Z"},
        "packages": {"apache2": package},
        "ansible_facts": {"packages": {"apache2": package}},
        "services": {"apache2": {"name": "apache2", "state": "running"}},
    }
    (members / "gather/webserver/facts.json").write_text(json.dumps(facts))
    export = tmp_path / "otel.json"
    export.write_text(
        json.dumps(
            {
                "resourceLogs": [
                    {
                        "resource": {},
                        "scopeLogs": [
                            {
                                "logRecords": [
                                    {
                                        "body": {"stringValue": body},
                                        "observedTimeUnixNano": "1775919754569766460",
                                    }
                                ]
                            }
                        ],
                    }
                ]
            }
        )
        + "\n"
    )
    binding = tmp_path / "binding.json"
    prepare_binding(export, members, binding)
    case = TelemetryInput(
        service_name="apache2",
        service_instance_id="dataset:russellmitchell:webserver:apache2",
        package_name="Apache",
        start_time="2026-04-11T14:00:00Z",
        end_time="2026-04-12T14:00:00Z",
    )
    return export, binding, members, case


def acquire(files, **overrides):
    export, binding, _, case = files
    options = dict(source_id="synthetic-apache", acquisition="recorded", apache_binding=binding)
    options.update(overrides)
    return read_snapshot(export, case.query(), **options)


def test_runtime_inventory_and_source_attribution_remain_distinct(apache_files):
    data = acquire(apache_files)
    evidence = evidence_from_snapshot(data)
    assert evidence.software[0].package == "Apache"
    assert evidence.software[0].version == "2.4.29"
    c = evidence.telemetry.recorded_context
    assert c.package_version == "2.4.29-1ubuntu4.21"
    assert c.instance_basis == "dataset-host-service-scope"
    assert data.observations[0].original_log.line == 1
    assert data.observations[0].original_log.event_time_text.startswith("Mon Jan 24")
    assert evidence.endpoint_exposed is None and evidence.deserialization_observed is None
    assert "not an observed runtime instance ID" in evidence.observations[-1]


def test_parser_without_binding_does_not_invent_identity(apache_files):
    data = acquire(apache_files, apache_binding=None)
    assert not data.observations
    with pytest.raises(ValueError, match="No supported observations"):
        evidence_from_snapshot(data)


@pytest.mark.parametrize("target", ["export", "facts", "log"])
def test_changed_sources_rejected(apache_files, target):
    export, _, members, _ = apache_files
    path = {
        "export": export,
        "facts": members / "gather/webserver/facts.json",
        "log": members / "gather/webserver/logs/apache2/error.log.1",
    }[target]
    path.write_bytes(path.read_bytes() + b" ")
    with pytest.raises(ValueError, match="changed|match export"):
        acquire(apache_files)


def test_binding_cannot_claim_live_or_lose_context(apache_files):
    with pytest.raises(ValueError, match="recorded acquisition"):
        acquire(apache_files, acquisition="collector-file")
    data = acquire(apache_files).model_dump(mode="json")
    data["recorded_context"] = None
    with pytest.raises(ValueError, match="context"):
        TelemetrySnapshot.model_validate(data)


@pytest.mark.parametrize("fault", ["missing", "duplicate", "resource"])
def test_exact_unique_original_and_unattributed_resource_required(apache_files, fault):
    export, binding, members, _ = apache_files
    original = members / "gather/webserver/logs/apache2/error.log.1"
    if fault == "missing":
        original.write_text("different original log\n")
    elif fault == "duplicate":
        (original.parent / "error.log.2").write_bytes(original.read_bytes())
    else:
        doc = json.loads(export.read_text())
        doc["resourceLogs"][0]["resource"]["attributes"] = [
            {"key": "service.name", "value": {"stringValue": "different"}}
        ]
        export.write_text(json.dumps(doc))
    binding.unlink()
    prepare_binding(export, members, binding)
    with pytest.raises(ValueError, match="unique|resource attributes"):
        acquire(apache_files)


def test_inventory_tampering_rejected_at_publication(apache_files, tmp_path):
    data = acquire(apache_files)

    class Source:
        def collect(self, query):
            return data

    session = ArtifactSession(apache_files[3], tmp_path / "run", telemetry_tool=Source())
    payload = session.collect_runtime_evidence()
    payload["telemetry"]["recorded_context"]["package_version"] = "invented"
    with pytest.raises(ValueError, match="exact evidence"):
        session.publish_runtime_evidence(json.dumps(payload))


@pytest.mark.mcp_http
def test_http_camel_strategic_receives_recorded_inventory(apache_files, tmp_path):
    from test_camel_integration import ScriptedToolModel

    export, binding, _, case = apache_files
    server = ThreadingHTTPServer(
        ("127.0.0.1", 0), handler_for(export, "synthetic-apache", "recorded", binding)
    )
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    queried = []

    class Lookup:
        def lookup_vulnerabilities(self, software):
            queried.append(software)
            return LookupResult(status="unsupported", vulnerabilities=[])

    try:
        settings = TelemetryHTTPSettings(
            url=f"http://127.0.0.1:{server.server_port}/v1/observations",
            source_id="synthetic-apache",
            acquisition="recorded",
        )
        session = ArtifactSession(
            case,
            tmp_path / "run",
            mode="camel",
            telemetry_tool=HTTPTelemetryTool(settings, lambda event: None),
        )
        session.vulnerability_tool = Lookup()
        model = ScriptedToolModel(session)
        decision = run_camel(session, lambda: model)
        assert session.assert_complete() == decision
        assert decision.status == "insufficient_evidence"
        assert queried[0].package == "Apache" and queried[0].version == "2.4.29"
        context = model.received_contexts["strategic"]["artifacts"]
        evidence = session.require("runtime_evidence", RuntimeEvidence)
        assert context["runtime_evidence"] == evidence.model_dump(mode="json")
        assert (
            context["runtime_evidence"]["telemetry"]["recorded_context"]["package_version"]
            == "2.4.29-1ubuntu4.21"
        )
        assert context["vulnerability_report"]["vulnerabilities"] == []
        assert context["candidate_strategies"]["strategies"] == []
        assert "inventory package revision remain separate" in decision.explanation
        assert evidence.telemetry.source_sha256 == hashlib.sha256(export.read_bytes()).hexdigest()
    finally:
        server.shutdown()
        thread.join(timeout=5)
        server.server_close()
