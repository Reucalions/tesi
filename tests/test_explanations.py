"""La struttura Pydantic non rende vero il testo libero: verifichiamo il confine.

Le alterazioni dello stato privato simulano corruzioni, non un'API degli agenti.
"""

import pytest
from pydantic import ValidationError

from thesis_agents.fixtures import fixture_candidates, fixture_evidence, run_fixtures
from thesis_agents.orchestration.artifacts import ArtifactSession, json_payload
from thesis_agents.schemas import FinalDecision


def publish_with_commentary(session, commentary, *, invented_narrative=None):
    evidence = fixture_evidence(session)
    if invented_narrative:
        evidence.observations = [invented_narrative]
    session.publish_runtime_evidence(json_payload(evidence))
    report = session.lookup_vulnerabilities()
    session.publish_vulnerability_report(json_payload(report))
    candidates = fixture_candidates([v["cve_id"] for v in report["vulnerabilities"]])
    if invented_narrative:
        for candidate in candidates.strategies:
            candidate.description = invented_narrative
            candidate.rationale = invented_narrative
    session.publish_candidate_strategies(json_payload(candidates))
    session.build_argumentation_graph()
    ranking = session.rank_graph()
    selected = None
    for item in ranking["ranking"]:
        if session.validate_countermeasure(item["strategy_id"])["valid"]:
            selected = item["strategy_id"]
            break
    session.publish_final_decision(selected, commentary)
    session.record_provenance()
    return session.assert_complete()


def test_invented_prose_is_preserved_but_not_promoted_to_evidence(session):
    invented = "Upgrade to 99.99.99 per vendor bulletin FAKE-123; measured benefit is 100%."
    decision = publish_with_commentary(session, invented, invented_narrative=invented)
    assert decision.explanation_method == "artifact-derived-v1"
    assert decision.agent_commentary.text == invented
    assert decision.agent_commentary.verification == "unverified"
    for unsupported_claim in ("99.99.99", "FAKE-123", "100%"):
        assert unsupported_claim not in decision.explanation
    estimates = [c for c in decision.explanation_claims if c.category == "estimate"]
    assert len(estimates) == 4
    assert all("not measurements" in c.text for c in estimates)
    assert session.publish_final_decision("S_UPGRADE", invented) == decision.model_dump(mode="json")
    with pytest.raises(ValueError, match="immutable once published"):
        session.publish_final_decision("S_UPGRADE", "Changed commentary")


def test_unsupported_lookup_does_not_assert_software_safety_or_vendor_support(case, tmp_path):
    case.package_name = "demo-unsupported-package"
    session = ArtifactSession(case, tmp_path, mode="fixtures")
    misleading = (
        "No vulnerabilities because the package is unsupported, "
        "rendering every countermeasure invalid."
    )
    decision = publish_with_commentary(session, misleading)
    assert decision.status == "insufficient_evidence"
    assert misleading == decision.agent_commentary.text
    assert misleading not in decision.explanation
    assert "configured lookup does not cover this software/version" in decision.explanation
    assert "vendor support status remain unknown" in decision.explanation
    assert "empty findings list is not proof of safety" in decision.explanation
    assert "does not establish that every countermeasure is invalid" in decision.explanation


@pytest.mark.parametrize("alteration", ["text", "verified_commentary", "missing_claims"])
def test_schema_rejects_inconsistent_explanation_metadata(session, alteration):
    payload = run_fixtures(session).model_dump(mode="json")
    if alteration == "text":
        payload["explanation"] = "An unsupported assertion"
    elif alteration == "verified_commentary":
        payload["agent_commentary"]["verification"] = "verified"
    else:
        payload["explanation_claims"] = []
    with pytest.raises(ValidationError):
        FinalDecision.model_validate(payload)


@pytest.mark.parametrize("alteration", ["claim", "source", "legacy"])
def test_complete_rechecks_derivation_even_if_disk_matches_memory(session, alteration):
    payload = run_fixtures(session).model_dump(mode="json")
    if alteration == "claim":
        payload["explanation_claims"][0]["text"] = "Exploit confirmed without any evidence."
        payload["explanation"] = "\n\n".join(c["text"] for c in payload["explanation_claims"])
    elif alteration == "source":
        payload["explanation_claims"][0]["sources"][0]["pointer"] = "/nonexistent"
    else:
        for key in ("explanation_method", "explanation_claims", "agent_commentary"):
            payload.pop(key)
    # Sono tutti modelli validi localmente; serve la verifica contro la sessione.
    altered = FinalDecision.model_validate(payload)
    session._artifacts["final_decision"] = altered
    (session.output_dir / "final_decision.json").write_text(altered.model_dump_json())
    with pytest.raises(ValueError, match="derived from the current artifacts"):
        session.assert_complete()


def test_historical_decisions_remain_readable_without_becoming_verified(session):
    payload = run_fixtures(session).model_dump(mode="json")
    for key in ("explanation_method", "explanation_claims", "agent_commentary"):
        payload.pop(key)
    payload["explanation"] = "Historical free text, possibly inaccurate."
    historical = FinalDecision.model_validate(payload)
    assert historical.explanation_method == "legacy-unverified"
    assert historical.explanation_claims == []
    assert historical.agent_commentary is None
