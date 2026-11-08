"""Client di dominio del framework per il bridge condiviso, senza inferenza."""

from pathlib import Path
from typing import Literal

from pydantic import BaseModel, ConfigDict

from thesis_agents.mcp.client import MCPClient, MCPError, digest
from thesis_agents.mcp.operational_contracts import verify_operational_assessment
from thesis_agents.mcp.settings import MCPStdioSettings
from thesis_agents.mcp.shared_contracts import (
    RESPONSES,
    RankRemediationsRequest,
    RankRemediationsResponse,
    SharedDecision,
    SharedProvenance,
    SharedValidation,
    ValidateCountermeasureRequest,
    shared_contracts,
)


class SharedMCPProfile(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    version: Literal[1] = 1
    contract: Literal["shared-saas-v1"] = "shared-saas-v1"
    server_name: Literal["mcp-semantic-cti-saas"] = "mcp-semantic-cti-saas"
    connection: MCPStdioSettings

    @classmethod
    def load(cls, path: Path):
        return cls.model_validate_json(path.read_text())


class SharedServicesClient:
    def __init__(
        self,
        profile: SharedMCPProfile,
        *,
        audit=None,
        stderr_path: Path | None = None,
        finalization: bool = False,
    ):
        self.profile = SharedMCPProfile.model_validate(profile.model_dump())
        self.finalization_enabled = finalization
        contracts = shared_contracts()
        if finalization:
            from thesis_agents.mcp.finalization_contracts import finalization_contracts

            contracts.update(finalization_contracts())
        self.client = MCPClient(
            self.profile.connection,
            contracts=contracts,
            audit=audit,
            stderr_path=stderr_path,
        )
        self._decisions: dict[str, RankRemediationsResponse] = {}

    def __enter__(self):
        self.client.__enter__()
        if self.client.server_info["name"] != self.profile.server_name:
            self.client.__exit__(None, None, None)
            raise MCPError("Il server non corrisponde al bridge condiviso configurato")
        self._decisions.clear()
        return self

    def __exit__(self, *exc):
        return self.client.__exit__(*exc)

    def _call(self, action, arguments, verify, response_type=None):
        def parse(envelope):
            if (
                set(envelope) != {"ok", "action", "payload"}
                or envelope["ok"] is not True
                or envelope["action"] != action
            ):
                raise ValueError("Envelope del bridge incompatibile con l'azione richiesta")
            response = (response_type or RESPONSES[action]).model_validate(envelope["payload"])
            verify(response)
            return response

        return self.client.call_tool(action, arguments, parse)

    def rank_remediations(self, request: RankRemediationsRequest) -> RankRemediationsResponse:
        request = RankRemediationsRequest.model_validate(request.model_dump())

        def verify(response):
            expected = {c.id: c.name for c in request.candidates}
            if (
                response.cve_id != request.cve_id
                or response.status != "CURRENT"
                or {row.id: row.name for row in response.ranked_strategies} != expected
            ):
                raise ValueError("Ranking estraneo alla CVE o alle candidate richieste")
            if response.slsa_assurance.input_digest != f"sha256:{digest(request.rest_payload())}":
                raise ValueError("Digest del ranking estraneo alla richiesta REST equivalente")
            if (
                request.knowledge_snapshot_id is not None
                and response.knowledge_snapshot_id != request.knowledge_snapshot_id
            ):
                raise ValueError("Snapshot diverso da quello richiesto")
            previous = self._decisions.get(response.decision_id)
            if previous is not None and previous != response:
                raise ValueError("Identificativo di decisione riutilizzato per ranking differenti")

        result = self._call("rank_remediations", request.wire_payload(), verify)
        self._decisions[result.decision_id] = result.model_copy(deep=True)
        return result

    def validate_countermeasure(self, request: ValidateCountermeasureRequest) -> SharedValidation:
        request = ValidateCountermeasureRequest.model_validate(request.model_dump())

        def verify(response):
            if (
                response.reasoning.resource_iri != request.asset_iri
                or response.reasoning.request_iri != request.countermeasure_iri
            ):
                raise ValueError("Validazione riferita a IRI differenti")
            if (
                request.ontology_id is not None
                and response.reasoning.ontology_key != request.ontology_id
            ):
                raise ValueError("Validazione riferita a un'altra ontologia")
            if (request.operational_context is None) != (response.operational is None):
                raise ValueError("Contesto operativo omesso o aggiunto dal backend")
            if request.operational_context is not None:
                verify_operational_assessment(request.operational_context, response.operational)

        return self._call("validate_countermeasure", request.model_dump(exclude_none=True), verify)

    def _read(self, action, decision_id):
        from thesis_agents.mcp.shared_contracts import DecisionRequest

        request = DecisionRequest(decision_id=decision_id)

        def verify(response):
            if response.decision_id != decision_id:
                raise ValueError("Rilettura riferita a un'altra decisione")
            expected = self._decisions.get(decision_id)
            if expected is not None:
                assurance = response.slsa_assurance
                actual_digest = (
                    response.input_digest if action == "get_decision" else assurance.input_digest
                )
                if (
                    actual_digest != expected.slsa_assurance.input_digest
                    or response.knowledge_snapshot_id != expected.knowledge_snapshot_id
                    or response.knowledge_snapshot_digest != expected.knowledge_snapshot_digest
                ):
                    raise ValueError("Rilettura non coerente con il ranking registrato")
                if action == "get_decision" and (
                    response.ranked_strategies != expected.ranked_strategies
                    or response.cve_id != expected.cve_id
                    or response.tenant_id != expected.tenant_id
                    or response.revision != expected.revision
                    or response.status != expected.status
                    or response.ontology_digest != expected.slsa_assurance.ontology_digest
                ):
                    raise ValueError("Decisione riletta diversa da quella ricevuta")
                if assurance != expected.slsa_assurance:
                    raise ValueError("Assurance della provenance diversa da quella originale")

        return self._call(action, request.model_dump(), verify)

    def get_decision(self, decision_id: str) -> SharedDecision:
        return self._read("get_decision", decision_id)

    def get_provenance(self, decision_id: str) -> SharedProvenance:
        return self._read("get_provenance", decision_id)

    def finalize_recommendation(self, document_json):
        from thesis_agents.mcp.finalization_contracts import (
            FinalizationDocument,
            FinalizationResponse,
            strict_json,
        )

        if not self.finalization_enabled:
            raise MCPError("Shared finalization tools were not authorized for this client")
        document = FinalizationDocument.model_validate(strict_json(document_json))

        def verify(response):
            if (
                response.record.document_json != document_json
                or response.record.finalization_id != document.finalization_id
            ):
                raise ValueError("Finalized ledger document differs from fixed original request")
            previous = self._decisions.get(document.ranking_decision_id)
            if (
                previous is not None
                and response.record.provenance.slsa_assurance != previous.slsa_assurance
            ):
                raise ValueError("Finalization assurance differs from original ranking")

        return self._call(
            "finalize_recommendation",
            {"document_json": document_json},
            verify,
            FinalizationResponse,
        )

    def get_finalization(self, decision_id, finalization_id):
        from thesis_agents.mcp.finalization_contracts import FinalizationResponse

        if not self.finalization_enabled:
            raise MCPError("Shared finalization tools were not authorized for this client")

        def verify(response):
            if (
                response.record.document.ranking_decision_id != decision_id
                or response.record.finalization_id != finalization_id
            ):
                raise ValueError("Finalization readback differs from requested identity")

        return self._call(
            "get_finalization",
            {"decision_id": decision_id, "finalization_id": finalization_id},
            verify,
            FinalizationResponse,
        )
