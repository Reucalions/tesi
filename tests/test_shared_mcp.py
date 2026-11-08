"""Contratti nativi condivisi su stdio effettivo; server dichiaratamente simulato."""

import json

import pytest
from mcp.types import CallToolResult, TextContent
from test_mcp_stdio import assert_child_stopped, stdio_settings

from thesis_agents.mcp.client import MCPError, MCPToolError, decode_result
from thesis_agents.mcp.shared_client import SharedMCPProfile, SharedServicesClient
from thesis_agents.mcp.shared_contracts import (
    RankRemediationsRequest,
    ValidateCountermeasureRequest,
)


def rank_request():
    return RankRemediationsRequest(
        cve_id="CVE-2025-0160",
        candidates=[{"id": "S_PATCH", "name": "Patch"}],
        knowledge_snapshot_id="fixture-snapshot",
    )


def validation_request():
    return ValidateCountermeasureRequest(
        asset_iri="asset", countermeasure_iri="cm-conflict", ontology_id="fixture-tbox"
    )


def client(tmp_path, fault="none", events=None, timeout=5):
    settings = stdio_settings(tmp_path, kind="shared", fault=fault).model_copy(
        update={"timeout_seconds": timeout}
    )
    return SharedServicesClient(
        SharedMCPProfile(connection=settings),
        audit=(events.append if events is not None else None),
        stderr_path=tmp_path / "stderr.log",
    )


def test_native_four_tools_preserve_scores_semantic_rejection_and_readback(tmp_path):
    events = []
    with client(tmp_path, events=events) as connection:
        ranking = connection.rank_remediations(rank_request())
        assert ranking.ranked_strategies[0].score == 10
        assert ranking.slsa_assurance.verified is False
        rejection = connection.validate_countermeasure(validation_request())
        assert rejection.valid is False and rejection.status == "rejected"
        assert rejection.conflict_penalty == 2
        decision = connection.get_decision(ranking.decision_id)
        provenance = connection.get_provenance(ranking.decision_id)
        assert decision.ranked_strategies == ranking.ranked_strategies
        assert provenance.slsa_assurance == ranking.slsa_assurance
    assert [e["tool"] for e in events if e["event"] == "tool_call"] == [
        "rank_remediations",
        "validate_countermeasure",
        "get_decision",
        "get_provenance",
    ]
    assert all(e["status"] == "validated" for e in events if e["event"] == "tool_call")
    assert_child_stopped(tmp_path / "child.pid")


@pytest.mark.parametrize("fault", ["missing", "bad-schema", "wrong-server"])
def test_shared_discovery_and_server_identity_fail_closed(tmp_path, fault):
    with pytest.raises(MCPError):
        with client(tmp_path, fault):
            pytest.fail("Incompatible bridge accepted")
    assert_child_stopped(tmp_path / "child.pid")


@pytest.mark.parametrize(
    "fault",
    [
        "wrong-cve",
        "wrong-candidate",
        "bad-score",
        "wrong-digest",
        "wrong-snapshot",
        "wrong-action",
        "disconnect",
        "timeout",
    ],
)
def test_invalid_ranking_or_transport_error_closes_process(tmp_path, fault):
    events = []
    connection = client(tmp_path, fault, events, timeout=2)
    with connection:
        with pytest.raises(MCPError):
            connection.rank_remediations(rank_request())
        assert connection.client._session is None
    assert events[-1]["status"] == "failed"
    assert_child_stopped(tmp_path / "child.pid")


@pytest.mark.parametrize("fault", ["wrong-iri", "wrong-ontology", "false-acceptance"])
def test_semantic_response_must_match_iris_ontology_and_native_result(tmp_path, fault):
    with client(tmp_path, fault) as connection:
        with pytest.raises(MCPError):
            connection.validate_countermeasure(validation_request())
    assert_child_stopped(tmp_path / "child.pid")


@pytest.mark.parametrize(
    "fault,tool",
    [
        ("read-cve", "get_decision"),
        ("read-ontology", "get_decision"),
        ("read-no-assurance", "get_decision"),
        ("read-snapshot", "get_decision"),
        ("read-snapshot", "get_provenance"),
        ("read-assurance", "get_provenance"),
    ],
)
def test_readback_cannot_replace_original_decision_context(tmp_path, fault, tool):
    with client(tmp_path, fault) as connection:
        ranking = connection.rank_remediations(rank_request())
        with pytest.raises(MCPError):
            getattr(connection, tool)(ranking.decision_id)
    assert_child_stopped(tmp_path / "child.pid")


def test_application_error_preserves_only_sanitized_code(tmp_path):
    events = []
    with client(tmp_path, "tool-error", events) as connection:
        with pytest.raises(MCPToolError, match="BACKEND_UNAVAILABLE") as caught:
            connection.rank_remediations(rank_request())
    assert caught.value.code == "BACKEND_UNAVAILABLE"
    assert events[-1]["error_code"] == "BACKEND_UNAVAILABLE"
    assert "ARBITRARY_REMOTE_SECRET" not in json.dumps(events) + str(caught.value)
    assert_child_stopped(tmp_path / "child.pid")


def test_arbitrary_error_code_is_not_forwarded():
    result = CallToolResult(
        isError=True,
        content=[
            TextContent(
                type="text", text=json.dumps({"ok": False, "errorCode": "remote secret\ntext"})
            )
        ],
    )
    with pytest.raises(MCPError, match="restituito un errore") as caught:
        decode_result(result)
    assert "remote secret" not in str(caught.value)


def test_shared_probe_checks_without_calls_and_validates_request_first(tmp_path, capsys):
    from thesis_agents.mcp.shared_probe import main

    profile = tmp_path / "profile.json"
    profile.write_text(
        SharedMCPProfile(connection=stdio_settings(tmp_path, kind="shared")).model_dump_json()
    )
    output = tmp_path / "probe"
    assert main(["--profile", str(profile), "--check-config", "--output-dir", str(output)]) == 0
    report = json.loads(capsys.readouterr().out)
    assert set(report["result"]["checked"]) == {
        "rank_remediations",
        "validate_countermeasure",
        "get_decision",
        "get_provenance",
    }
    assert [e["event"] for e in report["mcp_events"]] == ["connected"]
    assert_child_stopped(tmp_path / "child.pid")
    (tmp_path / "child.pid").unlink()
    request = tmp_path / "invalid.json"
    request.write_text('{"asset_iri":"asset"}')
    invalid_output = tmp_path / "invalid-output"
    assert (
        main(
            [
                "--profile",
                str(profile),
                "--tool",
                "validate_countermeasure",
                "--request",
                str(request),
                "--output-dir",
                str(invalid_output),
            ]
        )
        == 1
    )
    assert not invalid_output.exists() and not (tmp_path / "child.pid").exists()
    request.write_text(validation_request().model_dump_json())
    valid_output = tmp_path / "valid-output"
    assert (
        main(
            [
                "--profile",
                str(profile),
                "--tool",
                "validate_countermeasure",
                "--request",
                str(request),
                "--output-dir",
                str(valid_output),
            ]
        )
        == 0
    )
    capsys.readouterr()
    response = json.loads((valid_output / "response.json").read_text())
    assert response["result"]["status"] == "rejected"
    assert (valid_output / "request.json").exists()
    assert response["mcp_events"][-1]["status"] == "validated"
    assert_child_stopped(tmp_path / "child.pid")


@pytest.mark.parametrize(
    "invalid",
    [
        {"candidates": [{"id": "S1", "name": "A"}, {"id": "S1", "name": "B"}]},
        {"candidates": [{"id": "S1", "name": "A"}, {"id": "S2", "name": "A"}]},
        {"asset_context": {"risk": 0.5}},
        {"cve_id": "CVE-2025-0160,CVE-2025-0001"},
        {
            "graph": {
                "nodes": [{"id": "OTHER", "type": "strategy"}],
                "edges": [{"from": "OTHER", "to": "missing"}],
            }
        },
    ],
)
def test_native_request_scope_and_graph_references(invalid):
    with pytest.raises(ValueError):
        RankRemediationsRequest.model_validate({**rank_request().model_dump(), **invalid})
