# Dimostrazione ripetibile degli stessi contratti usati dagli agenti CAMEL.
# Qui le proposte sono dati prefissati: il flusso procedurale riguarda soltanto
# la prova senza LLM e non sostituisce l'orchestrazione multi-agente del prototipo.
"""Contract demonstration only. This module does NOT simulate a real CAMEL run."""

from thesis_agents.orchestration.artifacts import ArtifactSession, json_payload
from thesis_agents.schemas import CandidateStrategies, RuntimeEvidence, SoftwareObservation
from thesis_agents.schemas.countermeasure import CountermeasureCandidate


def fixture_evidence(session: ArtifactSession) -> RuntimeEvidence:
    # Copia i fatti del caso in un oggetto tipizzato, assegnando E1 all'osservazione
    # software. Non aggiunge misurazioni né deduce che un exploit sia stato eseguito.
    case = session.case
    return RuntimeEvidence(
        service_name=case.service_name,
        software=[
            SoftwareObservation(
                package=case.package_name, version=case.package_version, evidence_id="E1"
            )
        ],
        endpoint_exposed=case.endpoint_exposed,
        deserialization_observed=case.deserialization_observed,
        observations=["Static fixture input; no live instrumentation or exploit confirmation."],
    )


def fixture_candidates(cves: list[str]) -> CandidateStrategies:
    # Senza CVE note manca il fondamento per proporre strategie: il set è vuoto.
    # Il normale flusso CAMEL genera invece le candidate tramite CountermeasureAgent.
    if not cves:
        return CandidateStrategies(strategies=[])
    specs = [
        # Ogni tupla contiene ID, categoria, beneficio stimato, impatto operativo,
        # prerequisiti e descrizione. I numeri servono ai test, non sono misure reali.
        (
            "S_UPGRADE",
            "upgrade",
            0.95,
            0.20,
            ["maintenance_window", "package_upgrade"],
            "Upgrade Log4j after verifying vendor remediation and application compatibility.",
        ),
        (
            "S_ISOLATE",
            "isolate",
            0.80,
            0.50,
            ["network_isolation"],
            "Restrict payment-api network reachability as temporary containment.",
        ),
        (
            "S_BLOCK",
            "block_deployment",
            0.65,
            0.40,
            ["deployment_control"],
            "Prevent new deployments with the observed vulnerable package.",
        ),
        (
            "S_MONITOR",
            "monitor",
            0.20,
            0.10,
            ["monitoring"],
            "Increase detection coverage; this does not remediate the package vulnerability.",
        ),
    ]
    return CandidateStrategies(
        # Anche i dati statici attraversano Pydantic: una fixture incoerente deve
        # fallire come una proposta malformata prodotta da un agente.
        strategies=[
            CountermeasureCandidate(
                id=id_,
                action=action,
                description=description,
                addressed_vulnerabilities=cves,
                security_benefit=benefit,
                operational_impact=impact,
                prerequisites=prerequisites,
                constraints=["Illustrative fixture; assess effects before actual application."],
                rationale="Fixed contract example; scores are not empirical measurements.",
            )
            for id_, action, benefit, impact, prerequisites, description in specs
        ]
    )


def run_fixtures(session: ArtifactSession):
    # Il controllo di modalità impedisce di registrare questa dimostrazione come
    # una vera esecuzione CAMEL nella provenienza del run.
    if session.mode != "fixtures":
        raise ValueError("Fixture runs must explicitly use mode=fixtures")
    session.publish_runtime_evidence(json_payload(fixture_evidence(session)))
    # Il report nasce sempre dal tool di lookup: non si costruisce una scorciatoia
    # che aggiri la dipendenza software/versione dall'evidenza pubblicata.
    report = session.lookup_vulnerabilities()
    session.publish_vulnerability_report(json_payload(report))
    candidates = fixture_candidates([v["cve_id"] for v in report["vulnerabilities"]])
    session.publish_candidate_strategies(json_payload(candidates))
    session.build_argumentation_graph()
    ranking = session.rank_graph()
    # La classifica proviene dal backend. Si prova il primo elemento, poi si passa
    # al successivo solo se rifiutato: None rimane valido se nessuno è accettabile.
    selected = None
    for item in ranking["ranking"]:
        validation = session.validate_countermeasure(item["strategy_id"])
        if validation["valid"]:
            selected = item["strategy_id"]
            break
    session.publish_final_decision(
        selected,
        "Fixture contract run: first accepted ranked strategy, or no selection if none. "
        "All external backends are mocks; no CAMEL/LLM inference or remediation was executed.",
    )
    session.record_provenance()
    # Non basta produrre una decisione: devono esistere tutti gli artefatti previsti
    # e i loro file devono corrispondere agli oggetti validati nella sessione.
    return session.assert_complete()
