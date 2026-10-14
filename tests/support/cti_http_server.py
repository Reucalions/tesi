"""Replay dichiarato mock di risposte cve2owl catturate, solo per i test HTTP."""

import json
from pathlib import Path

from mcp.server.fastmcp import FastMCP

from thesis_agents.mcp.client import digest
from thesis_agents.mcp.cti_contracts import AssessmentRequest, AssessmentResponse, SoftwareQuery

DATA = Path(__file__).resolve().parents[1] / "data/cti"


def create_server(fault="none"):
    server = FastMCP("cti-test-replay", json_response=True, log_level="ERROR")

    @server.tool()
    def assess_software(software: SoftwareQuery) -> AssessmentResponse:
        cases = {
            ("log4j-core", "2.14.1"): "runtime-package",
            ("Apache Log4j2", "2.14.1"): "canonical-log4j2",
            ("Apache Log4j Core", "2.14.1"): "canonical-log4j-core",
            ("Apache Log4j Core", "2.25.4"): "core-negative",
            ("zzzzcostathesisabsent9f832c", "1.0"): "absent-product",
        }
        data = json.loads((DATA / f"{cases[software.product, software.version]}.json").read_text())
        # È un replay adattato alla richiesta, non una nuova interrogazione del KG.
        # Anche dataset e motore dichiarano esplicitamente la natura sintetica.
        data.update(
            backend_kind="mock",
            dataset={"id": "cti-test-replay", "kind": "fixture", "sha256": "a" * 64},
            engine_sha256={"cti-test-replay": "b" * 64},
            software=software.model_dump(mode="json"),
            request_sha256=digest(AssessmentRequest(software=software).model_dump(mode="json")),
        )
        for result in [data["matching"], *data["assessment"]["results"]]:
            result["asset"]["vendor"] = software.vendor
            result["query"]["vendor"] = software.vendor
            result["query"]["normalized_vendor"] = software.vendor or ""
        if fault == "wrong-kind":
            data["backend_kind"] = "real"
        elif fault == "wrong-evidence":
            data["software"]["evidence_id"] = "another-observation"
        return AssessmentResponse.model_validate(data)

    return server
