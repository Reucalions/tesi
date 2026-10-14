"""Discovery e validazione condivise per il contratto cve2owl-assessment-v1."""

from thesis_agents.mcp.client import digest
from thesis_agents.mcp.cti_contracts import TOOL, AssessmentRequest, AssessmentResponse


def cti_contracts() -> dict:
    return {TOOL: (AssessmentRequest.model_json_schema(), AssessmentResponse.model_json_schema())}


def validate_response(payload: dict, request: AssessmentRequest, expected_kind: str):
    """Controlla forma, destinatario della risposta e dichiarazione della fonte.

    Hash e backend_kind consentono verifiche di coerenza, non attestano da soli
    autenticità del server, qualità dei dati o correttezza delle sue valutazioni.
    """
    result = AssessmentResponse.model_validate(payload)
    if result.backend_kind != expected_kind:
        raise ValueError("Tipo di backend diverso da quello richiesto")
    dataset_kind = "fixture" if expected_kind == "mock" else "real"
    if result.dataset.kind != dataset_kind:
        raise ValueError("Tipo di dataset incoerente con il backend dichiarato")
    if result.request_sha256 != digest(request.model_dump(mode="json")):
        raise ValueError("Hash della richiesta non corrispondente")
    if result.software != request.software:
        raise ValueError("Il backend ha modificato il software o il riferimento all'evidenza")
    if not result.engine_sha256:
        raise ValueError("Identificazione del motore di correlazione assente")
    asset = result.matching.asset
    if (asset.product, asset.version, asset.vendor) != (
        request.software.product,
        request.software.version,
        request.software.vendor,
    ):
        raise ValueError("Il matching riguarda un asset diverso dalla richiesta")
    assessments = result.assessment.results
    eligible = [m for m in result.matching.matches if m.confidence == "high"]
    # La baseline esclude dalla valutazione i match sotto soglia e gli asset
    # privi di match ammissibili. Restano visibili nel risultato di matching.
    if len(assessments) != int(bool(eligible)):
        raise ValueError("Numero di asset valutati incoerente con la policy")
    if assessments and assessments[0].asset != asset:
        raise ValueError("La valutazione riguarda un asset diverso dalla richiesta")
    assessed = assessments[0].matches if assessments else []
    if [m.canonical_id for m in eligible] != [m.canonical_id for m in assessed]:
        raise ValueError("Le identità valutate differiscono da quelle restituite dal matching")
    ids = [m.canonical_id for m in result.matching.matches]
    if len(ids) != len(set(ids)):
        raise ValueError("Identità CTI duplicate")
    identity_fields = {
        "canonical_id",
        "vendor",
        "product",
        "normalized_vendor",
        "normalized_product",
        "confidence",
        "score",
        "affected_count",
        "evidence",
    }
    entry_fields = {
        "affected_product_id",
        "cve_id",
        "affected_iri",
        "json_path",
        "vendor",
        "product",
    }
    for original, evaluated in zip(eligible, assessed, strict=True):
        if original.model_dump(include=identity_fields) != evaluated.model_dump(
            include=identity_fields
        ):
            raise ValueError("Identità alterata fra matching e valutazione")
        if [e.model_dump(include=entry_fields) for e in original.affected_entries] != [
            e.model_dump(include=entry_fields) for e in evaluated.affected_entries
        ]:
            raise ValueError("Fonti CVE alterate fra matching e valutazione")
    summary = result.assessment.assessment_summary
    if (
        summary.assets_total != 1
        or summary.assets_with_assessments != len(assessments)
        or summary.matches_total != len(result.matching.matches)
        or summary.matches_evaluated != len(eligible)
        or summary.matches_skipped_by_confidence != len(result.matching.matches) - len(eligible)
        or summary.confidence_required != result.policy.confidence_levels
    ):
        raise ValueError("Riepilogo delle valutazioni incoerente con i risultati")
    return result
