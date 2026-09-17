"""Verifica il confine FunctionTool con oggetti JSON e contratti invariati."""

import asyncio
import json

import pytest

from thesis_agents.fixtures import fixture_candidates, fixture_evidence
from thesis_agents.orchestration.publication_tools import PublicationTools


def test_structured_tools_publish_all_three_artifacts(session):
    publications = PublicationTools(session)
    evidence = fixture_evidence(session).model_dump(mode="json")
    # Attraversa anche il percorso asincrono usato dai worker CAMEL.
    result = asyncio.run(
        publications.resolve("publish_runtime_evidence").async_call(payload=evidence)
    )
    assert result == evidence
    report = session.lookup_vulnerabilities()
    assert publications.resolve("publish_vulnerability_report")(payload=report) == report
    candidates = fixture_candidates([v["cve_id"] for v in report["vulnerabilities"]]).model_dump(
        mode="json"
    )
    assert publications.resolve("publish_candidate_strategies")(payload=candidates) == candidates
    context = session.get_context()
    assert context["artifacts"]["runtime_evidence"] == evidence
    assert context["artifacts"]["vulnerability_report"] == report
    assert context["artifacts"]["candidate_strategies"] == candidates


@pytest.mark.parametrize(
    "name",
    ["publish_runtime_evidence", "publish_vulnerability_report", "publish_candidate_strategies"],
)
def test_camel_publication_schema_requires_object(session, name):
    tool = PublicationTools(session).resolve(name)
    parameters = tool.get_openai_tool_schema()["function"]["parameters"]
    payload = parameters["properties"]["payload"]
    if "$ref" in payload:
        payload = parameters["$defs"][payload["$ref"].rsplit("/", 1)[-1]]
    assert payload["type"] == "object"
    assert payload["additionalProperties"] is False


def test_structured_tool_rejects_serialized_json_and_preserves_facts(session):
    tool = PublicationTools(session).resolve("publish_runtime_evidence")
    evidence = fixture_evidence(session).model_dump(mode="json")
    for malformed in (
        json.dumps(evidence),
        {**evidence, "endpoint_exposed": "true"},
        {**evidence, "service_name": "invented-service"},
        {**evidence, "extra_field": True},
    ):
        with pytest.raises(ValueError):
            tool(payload=malformed)
        assert not (session.output_dir / "runtime_evidence.json").exists()


def test_structured_tool_keeps_report_authority_and_immutability(session):
    publications = PublicationTools(session)
    evidence_tool = publications.resolve("publish_runtime_evidence")
    evidence = fixture_evidence(session).model_dump(mode="json")
    evidence_tool(payload=evidence)
    before = (session.output_dir / "runtime_evidence.json").read_bytes()
    with pytest.raises(ValueError):
        evidence_tool(payload={**evidence, "observations": ["Replace earlier evidence"]})
    report = session.lookup_vulnerabilities()
    report["vulnerabilities"][0]["cvss"] = 1.0
    with pytest.raises(ValueError, match="preserve its exact report"):
        publications.resolve("publish_vulnerability_report")(payload=report)
    assert (session.output_dir / "runtime_evidence.json").read_bytes() == before
    assert not (session.output_dir / "vulnerability_report.json").exists()
