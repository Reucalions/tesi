"""Guarded finalization uses original checkpoints; backend here is explicitly synthetic."""

import json

import pytest
import test_native_selection as selection_tests
from support.finalization_fixture import response_for

from thesis_agents.mcp.client import MCPError
from thesis_agents.mcp.finalization_contracts import FinalizationResponse, strict_json
from thesis_agents.mcp.shared_client import SharedMCPProfile, SharedServicesClient
from thesis_agents.strategic.finalization_agent import (
    build_finalization_agent,
    run_finalization_agent,
)
from thesis_agents.strategic.finalization_session import NativeFinalizationSession
from thesis_agents.strategic.selection_session import NativeSelectionSession

canonical_prepared = selection_tests.canonical_prepared
ranked = selection_tests.ranked


class BackendFixture:
    finalization_enabled = True

    def __init__(self, selection, checkpoint):
        self.profile = SharedMCPProfile.load(selection / "validation-input/mcp-profile.json")
        self.ranking = checkpoint._checkpoint[2]
        self.records, self.calls = {}, []
        self.fault = None

    def finalize_recommendation(self, raw):
        self.calls.append("finalize")
        if self.fault == "timeout":
            raise MCPError("uncertain fixture submission")
        data = json.loads(raw)
        native = next(
            r.ranking for r in self.ranking.results if r.cve_id == data["recommendation"]["cve_id"]
        )
        response = FinalizationResponse.model_validate(
            response_for(raw, native.slsa_assurance.model_dump(by_alias=True, exclude_none=True))
        )
        self.records[response.record.finalization_id] = response
        return response

    def get_finalization(self, decision_id, finalization_id):
        self.calls.append("read")
        response = self.records[finalization_id].model_copy(deep=True)
        assert response.record.document.ranking_decision_id == decision_id
        if self.fault == "readback":
            response.commit.block_number = "43"
        return response


@pytest.fixture
def selected(ranked, tmp_path):
    directory, _ = selection_tests.validated_case(ranked, tmp_path)
    selection = NativeSelectionSession(directory, tmp_path / "selection")
    selection.publish_native_recommendation()
    return selection, BackendFixture(selection.output_dir, selection)


def finish(session):
    session.get_context()
    while operation := session.next_operation():
        getattr(session, operation["tool"])()
    return session.assert_complete()


def test_per_cve_finalization_keeps_original_checkpoint_and_all_producer_hashes(selected, tmp_path):
    selection, backend = selected
    before = {str(p): p.read_bytes() for p in selection.output_dir.rglob("*") if p.is_file()}
    session = NativeFinalizationSession(selection.output_dir, tmp_path / "finalized", backend)
    result = finish(session)
    assert len(result.results) == 2
    assert backend.calls == ["finalize", "read", "finalize", "read"]
    assert [
        r.record.document.recommendation for r in result.results
    ] == selection.assert_complete().results
    assert all(len(r.record.document.source_digests) == 8 for r in result.results)
    assert result.shared_finalization == "completed" and result.deployment_verified is False
    assert result.verification_scope == "backend_reported_commit_and_readback"
    assert before == {
        str(p): p.read_bytes() for p in selection.output_dir.rglob("*") if p.is_file()
    }


@pytest.mark.parametrize("fault", ["timeout", "readback"])
def test_technical_failure_is_latched_without_automatic_retry_or_publication(
    selected, tmp_path, fault
):
    selection, backend = selected
    backend.fault = fault
    session = NativeFinalizationSession(selection.output_dir, tmp_path / "failed", backend)
    with pytest.raises((ValueError, MCPError)):
        finish(session)
    assert session._failed and session.next_operation() is None
    with pytest.raises(ValueError):
        session.finalize_recommendation()
    assert backend.calls.count("finalize") == 1
    assert not (session.output_dir / "native_strategic_finalization.json").exists()
    assert list((session.output_dir / "native").rglob("document.json"))


@pytest.mark.parametrize("scope", ["input", "copy", "request", "response", "publication"])
def test_tampering_is_detected_at_each_boundary(selected, tmp_path, scope):
    selection, backend = selected
    session = NativeFinalizationSession(selection.output_dir, tmp_path / "finalized", backend)
    if scope in ("input", "copy"):
        root = selection.output_dir if scope == "input" else session.output_dir / "selection-input"
        (root / "native_strategic_recommendation.json").write_text("{}")
    elif scope == "request":
        session.finalize_recommendation()
        next((session.output_dir / "native").rglob("document.json")).write_text("{}")
    elif scope == "response":
        session.finalize_recommendation()
        next((session.output_dir / "native").rglob("finalize_recommendation.json")).write_text("{}")
    else:
        finish(session)
        (session.output_dir / "native_strategic_finalization.json").write_text("{}")
    with pytest.raises(ValueError):
        session.assert_complete()


@pytest.mark.parametrize("change", ["selection", "kind", "authorization"])
def test_bad_checkpoint_or_backend_is_rejected_before_any_calls(selected, tmp_path, change):
    selection, backend = selected
    if change == "selection":
        (selection.output_dir / "native_strategic_recommendation.json").write_text("{}")
    elif change == "kind":
        payload = backend.profile.model_dump(mode="json")
        payload["connection"]["expected_kind"] = "real"
        backend.profile = SharedMCPProfile.model_validate(payload)
    else:
        backend.finalization_enabled = False
    with pytest.raises(ValueError):
        NativeFinalizationSession(selection.output_dir, tmp_path / "invalid", backend)
    assert not backend.calls and not (tmp_path / "invalid").exists()


@pytest.mark.parametrize(
    "tamper", ["digest", "commit", "transaction", "source", "choice", "dangling", "disconnected"]
)
def test_contract_refuses_altered_backend_records_even_when_hashes_are_recomputed(
    selected, tmp_path, tamper
):
    from thesis_agents.mcp.finalization_contracts import raw_digest

    selection, backend = selected
    session = NativeFinalizationSession(selection.output_dir, tmp_path / "finalized", backend)
    payload = finish(session).results[0].model_dump(mode="json", by_alias=True)
    if tamper == "digest":
        payload["record"]["document_sha256"] = "sha256:" + "0" * 64
    elif tamper == "commit":
        payload["commit"]["successful"] = False
    elif tamper == "transaction":
        payload["commit"]["transaction_id"] = "foreign"
    else:
        prov = json.loads(payload["record"]["provenance_json"])
        if tamper == "source":
            next(e for e in prov["entities"] if e.get("attributes", {}).get("artifact_name"))[
                "attributes"
            ]["sha256"] = "sha256:" + "0" * 64
        elif tamper == "choice":
            prov["entities"][0]["attributes"]["selected_strategy_id"] = "S_ISOLATE"
        elif tamper == "dangling":
            prov["relations"][0]["object"] = "urn:foreign"
        else:
            prov["relations"] = [
                r
                for r in prov["relations"]
                if not r["object"].startswith("urn:cti:fixture:validation")
            ]
        payload["record"]["provenance_json"] = json.dumps(prov)
        payload["record"]["provenance_sha256"] = raw_digest(payload["record"]["provenance_json"])
    with pytest.raises(ValueError):
        FinalizationResponse.model_validate(payload)


def test_optional_extension_keeps_default_four_tool_authorization(selected):
    selection, backend = selected
    legacy = SharedServicesClient(backend.profile)
    assert len(legacy.client.contracts) == 4
    with pytest.raises(MCPError):
        legacy.get_finalization("decision", "FIN_" + "0" * 64)
    extension = SharedServicesClient(backend.profile, finalization=True)
    assert len(extension.client.contracts) == 6
    for raw in ['{"x":1,"x":2}', '{"outer":{"x":1,"\\u0078":2}}', '{"x":NaN}']:
        with pytest.raises(ValueError):
            strict_json(raw)


def test_camel_tools_publish_and_policy_clone_retains_the_finalization_contract(selected, tmp_path):
    from test_camel_integration import ScriptedToolModel

    class SelectionModel(ScriptedToolModel):
        def _run(self, messages, response_format=None, tools=None):
            names = {t["function"]["name"] for t in tools or []}
            if not names:
                return self._completion(content="Published")
            assert len(names) == 1
            name = names.pop()
            self.tool_calls.append(name)
            return self._completion(
                tool_calls=[
                    {
                        "id": f"call-{len(self.tool_calls)}",
                        "type": "function",
                        "function": {"name": name, "arguments": "{}"},
                    }
                ]
            )

    selection, backend = selected
    session = NativeFinalizationSession(selection.output_dir, tmp_path / "camel-finalized", backend)
    model = SelectionModel(session)
    agent = build_finalization_agent(session, model)
    assert agent.clone().clone().tool_policy.session is session
    result = run_finalization_agent(session, model)
    assert result.shared_finalization == "completed"


def test_agent_receipt_views_preserve_full_records_and_original_source_context(selected, tmp_path):
    from thesis_agents.strategic.finalization_agent import _finalization_tool

    selection, backend = selected
    session = NativeFinalizationSession(selection.output_dir, tmp_path / "views", backend)
    assert _finalization_tool(session, "get_context")() == session.get_context()
    views = []
    while operation := session.next_operation():
        view = _finalization_tool(session, operation["tool"])()
        views.append(view)
        assert "document_json" not in json.dumps(view)
        assert "provenance_json" not in json.dumps(view)
    artifact = session.assert_complete()
    assert len(artifact.results) == 2
    for response in artifact.results:
        stored = response.model_dump(mode="json", by_alias=True)
        matching = [
            v
            for v in views[:-1]
            if v["record"]["finalization_id"] == response.record.finalization_id
        ]
        assert len(matching) == 2
        for view in matching:
            assert view["commit"] == stored["commit"]
            assert view["ledger_readback_verified"] is True
            assert view["record"]["document_sha256"] == response.record.document_sha256
            assert view["record"]["provenance_sha256"] == response.record.provenance_sha256
            assert len(json.dumps(view)) < len(json.dumps(stored)) / 2
        path = session.output_dir / "native" / response.record.document.recommendation.cve_id
        assert json.loads((path / "get_finalization.json").read_bytes()) == stored
    assert views[-1]["shared_finalization"] == "completed"
    assert len(views[-1]["results"]) == 2


def test_agent_receipt_view_cannot_hide_readback_failure(selected, tmp_path):
    from thesis_agents.strategic.finalization_agent import _finalization_tool

    selection, backend = selected
    session = NativeFinalizationSession(selection.output_dir, tmp_path / "views-failed", backend)
    _finalization_tool(session, "finalize_recommendation")()
    backend.fault = "readback"
    with pytest.raises(ValueError):
        _finalization_tool(session, "read_finalization")()
    assert session._failed
    assert not (session.output_dir / "native_strategic_finalization.json").exists()
