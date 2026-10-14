"""SBOM/OSV: identità esplicite, paginazione completa e contesto consegnato da CAMEL."""

import copy
import importlib.util
import json
import socket
import subprocess
import sys
import time
from pathlib import Path

import httpx
import pytest

from thesis_agents.backends import BackendSettings, connect_backends
from thesis_agents.fixtures import fixture_candidates, fixture_evidence
from thesis_agents.main import main
from thesis_agents.orchestration.artifacts import ArtifactSession
from thesis_agents.orchestration.workforce import run_camel
from thesis_agents.schemas import LookupResult, ProvenanceRecord, VulnerabilityReport
from thesis_agents.schemas.supply_chain import (
    AssetBinding,
    SupplyChainQuery,
    SupplyChainSnapshot,
    countermeasure_context,
    select_component,
)
from thesis_agents.tools.sbom_http import HTTPSupplyChainTool, SupplyChainHTTPSettings

ROOT = Path(__file__).resolve().parents[1]
SERVER = ROOT / "services/sbom_gateway/server.py"
SBOM = ROOT / "services/sbom_gateway/data/log4j-demo.cdx.json"


@pytest.fixture
def gateway_module():
    spec = importlib.util.spec_from_file_location("sbom_gateway_test", SERVER)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def query(case):
    return SupplyChainQuery(
        service_name=case.service_name,
        software={
            "package": case.package_name,
            "version": case.package_version,
            "evidence_id": "E1",
        },
    )


@pytest.fixture
def binding(case):
    return AssetBinding(
        service_name=case.service_name,
        runtime_package=case.package_name,
        component_ref="log4j-core",
    )


@pytest.fixture
def advisory():
    return {
        "id": "TEST-OSV-1",
        "modified": "2026-01-01T00:00:00Z",
        "aliases": ["CVE-2021-44228"],
        "affected": [
            {
                "package": {"ecosystem": "Maven", "name": "org.apache.logging.log4j:log4j-core"},
                "ranges": [
                    {"type": "ECOSYSTEM", "events": [{"introduced": "0"}, {"fixed": "2.15.0"}]}
                ],
            }
        ],
    }


@pytest.fixture
def snapshot(gateway_module, query, binding, advisory):
    gateway = gateway_module.Gateway(
        SBOM, binding, "test-sbom", "demo", "mock", "http://127.0.0.1/osv"
    )
    with httpx.Client(
        transport=httpx.MockTransport(lambda r: httpx.Response(200, json={"vulns": [advisory]}))
    ) as http:
        return gateway.assess(query, http)


@pytest.fixture
def report(case, tmp_path):
    session = ArtifactSession(case, tmp_path / "report")
    session.publish_runtime_evidence(fixture_evidence(session).model_dump_json())
    return VulnerabilityReport.model_validate(session.lookup_vulnerabilities())


@pytest.mark.parametrize(
    "fault", ["version", "asset", "binding", "purl", "duplicate", "format", "nested"]
)
def test_sbom_binding_rejects_incompatible_inventory(query, binding, fault):
    document = json.loads(SBOM.read_text())
    if fault == "version":
        query.software.version = "2.17.1"
    elif fault == "asset":
        query.service_name = "another-service"
    elif fault == "binding":
        binding.component_ref = "absent"
    elif fault == "purl":
        document["components"][0]["purl"] = "pkg:maven/another/component@2.14.1"
    elif fault == "duplicate":
        document["components"].append(document["components"][0])
    elif fault == "format":
        document["bomFormat"] = "SPDX"
    elif fault == "nested":
        document["components"][0]["components"] = [{}]
    with pytest.raises(ValueError):
        select_component(document, binding, query)


def test_context_preserves_range_branches_and_does_not_promote_osv_findings(
    snapshot, report, advisory
):
    payload = snapshot.model_dump(mode="json")
    first = payload["pages"][0]["response"]["vulns"][0]
    first["affected"][0]["ranges"].append(
        {"type": "ECOSYSTEM", "events": [{"introduced": "2.12.0"}, {"fixed": "2.12.2"}]}
    )
    first["affected"].append(
        {
            "package": {"ecosystem": "Maven", "name": "other:package"},
            "ranges": [{"type": "ECOSYSTEM", "events": [{"introduced": "0"}, {"fixed": "99"}]}],
        }
    )
    others = []
    for index in range(3):
        other = copy.deepcopy(advisory)
        other["id"] = f"TEST-OTHER-{index}"
        others.append(other)
    others[0]["aliases"] = ["CVE-2026-0001"]
    others[1]["withdrawn"] = "2026-02-01T00:00:00Z"
    others[2]["affected"][0]["package"]["name"] = "other:package"
    payload["pages"][0]["response"]["vulns"].extend(others)
    context = countermeasure_context(SupplyChainSnapshot.model_validate(payload), report)
    assert context.advisories[0].matched_cves == ["CVE-2021-44228"]
    assert len(context.advisories[0].ranges) == 2
    assert [r.events[-1].fixed for r in context.advisories[0].ranges] == ["2.15.0", "2.12.2"]
    assert context.other_osv_ids == ["TEST-OTHER-0"]
    assert context.withdrawn_ids == ["TEST-OTHER-1"]
    assert context.uncorrelated_ids == ["TEST-OTHER-2"]
    assert [v.cve_id for v in report.vulnerabilities] == ["CVE-2021-44228"]
    assert "details" not in context.model_dump_json()


def test_empty_osv_result_does_not_erase_cti_findings(snapshot, report):
    payload = snapshot.model_dump(mode="json")
    payload["pages"][0]["response"] = {}
    context = countermeasure_context(SupplyChainSnapshot.model_validate(payload), report)
    assert context.advisories == []
    assert context.report_cves_without_osv_match == ["CVE-2021-44228"]


def test_context_limit_does_not_silently_truncate_range_evidence(snapshot, report):
    payload = snapshot.model_dump(mode="json")
    affected = payload["pages"][0]["response"]["vulns"][0]["affected"][0]
    affected["ranges"][0]["events"][1]["fixed"] = "x" * (33 * 1024)
    with pytest.raises(ValueError, match="32 KiB"):
        countermeasure_context(SupplyChainSnapshot.model_validate(payload), report)


@pytest.mark.parametrize("fault", ["truncated", "query", "digest", "duplicate", "error"])
def test_snapshot_does_not_accept_incomplete_or_mismatched_osv(snapshot, fault):
    payload = snapshot.model_dump(mode="json")
    page = payload["pages"][0]
    if fault == "truncated":
        page["response"]["next_page_token"] = "next"
    elif fault == "query":
        page["request"]["version"] = "9.0"
    elif fault == "digest":
        payload["document_sha256"] = "0" * 64
    elif fault == "duplicate":
        page["response"]["vulns"] *= 2
    elif fault == "error":
        page["response"] = {"error": "rate limited"}
    with pytest.raises(ValueError):
        SupplyChainSnapshot.model_validate(payload)


def test_osv_pagination_is_completed_even_when_first_page_is_empty(
    gateway_module, query, binding, advisory
):
    calls = []

    def respond(request):
        body = json.loads(request.content)
        calls.append(body)
        return httpx.Response(
            200,
            json={"vulns": [advisory]} if "page_token" in body else {"next_page_token": "page-1"},
        )

    gateway = gateway_module.Gateway(
        SBOM, binding, "test-sbom", "demo", "mock", "http://127.0.0.1/osv"
    )
    with httpx.Client(transport=httpx.MockTransport(respond)) as http:
        result = gateway.assess(query, http)
    assert len(result.pages) == 2
    assert calls[1] == calls[0] | {"page_token": "page-1"}


def test_repeating_osv_page_token_fails(gateway_module):
    with httpx.Client(
        transport=httpx.MockTransport(
            lambda r: httpx.Response(200, json={"next_page_token": "same"})
        )
    ) as http:
        with pytest.raises(ValueError, match="repeated"):
            gateway_module.query_osv(
                {"package": {"name": "a", "ecosystem": "Maven"}, "version": "1"},
                "http://127.0.0.1/osv",
                http,
            )


@pytest.mark.parametrize("target", ["context", "snapshot"])
def test_publication_requires_context_and_tampering_blocks_downstream(
    case, tmp_path, snapshot, target
):
    class Source:
        calls = 0

        def collect(self, query):
            self.calls += 1
            # Il query/evidence id deriva dalla vera pubblicazione del test.
            data = snapshot.model_dump(mode="json")
            from thesis_agents.mcp.client import digest

            data["query"] = query.model_dump(mode="json")
            data["request_sha256"] = digest(data["query"])
            return SupplyChainSnapshot.model_validate(data)

    source = Source()
    session = ArtifactSession(case, tmp_path / "run", supply_chain_tool=source)
    session.publish_runtime_evidence(fixture_evidence(session).model_dump_json())
    session.publish_vulnerability_report(json.dumps(session.lookup_vulnerabilities()))
    candidates = fixture_candidates(["CVE-2021-44228"])
    with pytest.raises(ValueError, match="collect_countermeasure_context"):
        session.publish_candidate_strategies(candidates.model_dump_json())
    context = session.collect_countermeasure_context()
    assert session.collect_countermeasure_context() == context
    assert source.calls == 1
    session.publish_candidate_strategies(candidates.model_dump_json())
    filename = (
        "countermeasure_context.json" if target == "context" else "supply_chain_snapshot.json"
    )
    path = session.output_dir / filename
    saved = json.loads(path.read_text())
    saved["sbom_kind"] = "provided"
    path.write_text(json.dumps(saved))
    with pytest.raises(ValueError, match="snapshot/context"):
        session.build_argumentation_graph()


@pytest.fixture
def supply_chain_server(tmp_path, advisory):
    processes = []

    def launch(script, arguments):
        with socket.socket() as listener:
            listener.bind(("127.0.0.1", 0))
            listener.listen()
            base = f"http://127.0.0.1:{listener.getsockname()[1]}"
            log = (tmp_path / f"server-{len(processes)}.log").open("w+")
            process = subprocess.Popen(
                [sys.executable, str(script), "--fd", str(listener.fileno()), *arguments],
                pass_fds=(listener.fileno(),),
                stdout=log,
                stderr=log,
            )
            processes.append((process, log))
        with httpx.Client(timeout=0.2, trust_env=False) as http:
            for _ in range(200):
                if process.poll() is not None:
                    log.seek(0)
                    pytest.fail(log.read())
                try:
                    if http.get(base + "/health").status_code == 200:
                        return base
                except httpx.HTTPError:
                    pass
                time.sleep(0.02)
        pytest.fail("Supply chain server not ready")

    def start(*, status=200, pages=None):
        replies = tmp_path / "replies.json"
        requests = tmp_path / "requests.jsonl"
        replies.write_text(
            json.dumps(
                {"status": status, "pages": pages if pages is not None else [{"vulns": [advisory]}]}
            )
        )
        osv = launch(
            ROOT / "tests/support/osv_http_server.py",
            ["--replies", str(replies), "--requests", str(requests)],
        )
        gateway = launch(
            SERVER,
            [
                "--sbom",
                str(SBOM),
                "--source-id",
                "test-sbom",
                "--sbom-kind",
                "demo",
                "--service-name",
                "payment-api",
                "--runtime-package",
                "log4j-core",
                "--component-ref",
                "log4j-core",
                "--osv-kind",
                "mock",
                "--osv-url",
                osv + "/query",
            ],
        )
        return gateway + "/v1/enrichment", requests

    try:
        yield start
    finally:
        for process, log in reversed(processes):
            process.terminate()
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=5)
            log.close()


def settings_for(url, **overrides):
    return SupplyChainHTTPSettings(
        url=url, expected_kind="mock", source_id="test-sbom", sbom_kind="demo", **overrides
    )


@pytest.mark.mcp_http
@pytest.mark.parametrize("empty_cti", [False, True])
def test_real_http_camel_handoff_keeps_three_artifacts_and_additional_source(
    supply_chain_server, case, tmp_path, empty_cti
):
    from test_camel_integration import ScriptedToolModel

    url, requests = supply_chain_server()
    settings = BackendSettings(countermeasure_input=settings_for(url))
    session = ArtifactSession(case, tmp_path / "run", model="scripted-test-only")
    if empty_cti:

        class EmptyLookup:
            def lookup_vulnerabilities(self, software):
                return LookupResult(status="unsupported", vulnerabilities=[])

        session.vulnerability_tool = EmptyLookup()
    model = ScriptedToolModel(session)
    with connect_backends(session, settings):
        result = run_camel(session, lambda: model)
    assert result.status == ("insufficient_evidence" if empty_cti else "selected")
    context = model.received_contexts["countermeasure"]["external_inputs"]["countermeasure"][
        "context"
    ]
    if empty_cti:
        assert context["advisories"] == []
        assert context["other_osv_ids"] == ["TEST-OSV-1"]
    else:
        assert context["advisories"][0]["id"] == "TEST-OSV-1"
    assert model.tool_calls.count("collect_countermeasure_context") == 1
    assert len(requests.read_text().splitlines()) == 1
    strategic = model.received_contexts["strategic"]
    assert strategic["external_inputs"]["countermeasure"]["context"] == context
    for name in ("runtime_evidence", "vulnerability_report", "candidate_strategies"):
        assert strategic["artifacts"][name] == json.loads(
            (session.output_dir / f"{name}.json").read_text()
        )
    provenance = session.require("provenance", ProvenanceRecord)
    assert {"supply_chain_snapshot", "countermeasure_context"} <= {
        e.id for e in provenance.entities
    }
    assert (
        "countermeasure_context"
        in next(a for a in provenance.activities if a.id == "candidates").used
    )
    assert "SBOM kind=demo" in result.explanation and "OSV kind=mock" in result.explanation
    assert session.assert_complete() == result


@pytest.mark.mcp_http
@pytest.mark.parametrize("fault", ["http", "source", "kind", "pin", "version"])
def test_http_errors_do_not_fall_back(supply_chain_server, query, fault):
    url, _ = supply_chain_server(status=503 if fault == "http" else 200)
    settings = settings_for(url).model_dump()
    if fault == "source":
        settings["source_id"] = "wrong"
    elif fault == "kind":
        settings["expected_kind"] = "live"
    elif fault == "pin":
        settings["sbom_sha256"] = "0" * 64
    elif fault == "version":
        query.software.version = "99"
    events = []
    with pytest.raises(RuntimeError, match="collection failed"):
        HTTPSupplyChainTool(
            SupplyChainHTTPSettings.model_validate(settings), events.append
        ).collect(query)
    assert events[0]["status"] == "failed"


def test_fixtures_reject_network_input_before_starting(tmp_path, capsys):
    profile = tmp_path / "backends.json"
    profile.write_text(
        BackendSettings(
            countermeasure_input=settings_for("http://127.0.0.1:8005/v1/enrichment")
        ).model_dump_json()
    )
    assert (
        main(["--mode", "fixtures", "--backends", str(profile), "--output", str(tmp_path / "run")])
        == 1
    )
    assert "backend locali" in capsys.readouterr().err
    assert not (tmp_path / "run").exists()
