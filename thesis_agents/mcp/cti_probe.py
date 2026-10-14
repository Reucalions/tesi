"""Collaudo isolato del backend cve2owl attraverso MCP, senza agenti o LLM.

Il contratto in cti_contracts è una copia del contratto pubblico del servizio.
Nessun modulo del motore di correlazione viene importato nel processo tesi.
La risposta conserva la semantica del backend e non è un VulnerabilityReport.
"""

import argparse
import json
from pathlib import Path

from pydantic import ValidationError

from thesis_agents.mcp.client import MCPClient, MCPError, digest
from thesis_agents.mcp.cti_client import cti_contracts, validate_response
from thesis_agents.mcp.cti_contracts import (
    TOOL,
    AssessmentRequest,
    SoftwareQuery,
)
from thesis_agents.mcp.settings import MCPSettings


def run_probe(settings: MCPSettings, software: SoftwareQuery, output_dir: Path):
    """Salva richiesta, risposta e audit; una prova fallita resta riconoscibile."""
    request = AssessmentRequest(software=software)
    # Non sovrascrivere prove esistenti, incluse quelle fallite.
    output_dir.mkdir(parents=True, exist_ok=False)

    def write(name, value):
        (output_dir / name).write_text(
            json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n",
            encoding="utf-8",
        )

    write("request.json", request.model_dump(mode="json"))
    events = []
    summary = {
        "mode": "cti-probe",
        "llm_used": False,
        "endpoint": settings.url,
        "expected_kind": settings.expected_kind,
        "request_sha256": digest(request.model_dump(mode="json")),
        "status": "failed",
    }
    try:
        with MCPClient(settings, contracts=cti_contracts(), audit=events.append) as client:
            result = client.call_tool(
                TOOL,
                request.model_dump(mode="json"),
                lambda payload: validate_response(payload, request, settings.expected_kind),
            )
        write("assessment.json", result.model_dump(mode="json"))
        summary.update(
            status="validated",
            backend=result.backend,
            backend_kind=result.backend_kind,
            dataset=result.dataset.model_dump(mode="json"),
            engine_sha256=result.engine_sha256,
            response_sha256=digest(result.model_dump(mode="json")),
        )
        return result
    except Exception as error:
        summary["error_type"] = type(error).__name__
        raise
    finally:
        write("audit.json", events)
        write("summary.json", summary)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Collaudo MCP cve2owl senza LLM")
    parser.add_argument("--url", required=True)
    parser.add_argument("--expected-kind", choices=("mock", "real"), required=True)
    parser.add_argument("--product", required=True)
    parser.add_argument("--version")
    parser.add_argument("--vendor")
    parser.add_argument("--evidence-id", default="probe-E1")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--timeout", type=float, default=15)
    parser.add_argument("--token-env")
    args = parser.parse_args(argv)
    try:
        settings = MCPSettings(
            url=args.url,
            expected_kind=args.expected_kind,
            timeout_seconds=args.timeout,
            token_env=args.token_env,
        )
        software = SoftwareQuery(
            product=args.product,
            version=args.version,
            vendor=args.vendor,
            evidence_id=args.evidence_id,
        )
        result = run_probe(settings, software, args.output_dir)
    except (MCPError, ValidationError, OSError) as error:
        parser.exit(1, f"Collaudo fallito ({type(error).__name__}); nessun report pubblicato.\n")
    print(
        f"Risposta validata: {result.backend_kind}, dataset {result.dataset.id}. "
        f"Evidenze in {args.output_dir}. Non è una decisione della Workforce."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
