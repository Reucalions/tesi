"""Tool HTTP di sola lettura: nessuna lettura di file o script del backend nel MAS."""

import time
from datetime import UTC, datetime

import httpx

from thesis_agents.mcp.client import digest
from thesis_agents.schemas import RuntimeEvidence, SoftwareObservation
from thesis_agents.schemas.telemetry_source import (
    TelemetryQuery,
    TelemetryReference,
    TelemetrySnapshot,
)


def evidence_from_snapshot(snapshot: TelemetrySnapshot) -> RuntimeEvidence:
    """Mapping deterministico dei soli fatti espliciti, senza estrazione LLM implicita."""
    if snapshot.request_sha256 != digest(snapshot.query.model_dump(mode="json")):
        raise ValueError("Telemetry request digest mismatch")
    rows = snapshot.observations
    if not rows:
        raise ValueError("No supported observations in the requested window; no runtime evidence")
    if len({r.version for r in rows}) != 1:
        raise ValueError("Multiple observed versions: narrow the telemetry window")

    def aggregate(field):
        values = {getattr(r, field) for r in rows}
        return values.pop() if len(values) == 1 else None

    return RuntimeEvidence(
        service_name=snapshot.query.service_name,
        software=[
            SoftwareObservation(
                package=rows[0].package, version=rows[0].version, evidence_id=rows[0].evidence_id
            )
        ],
        endpoint_exposed=aggregate("endpoint_exposed"),
        deserialization_observed=aggregate("deserialization_observed"),
        observations=[
            f"{len(rows)} explicit OTEL log observations; acquisition={snapshot.acquisition}.",
            "Unknown flags remain null; observations do not establish an exploit.",
            "Identity is declared by instrumentation; this is not a complete software inventory.",
        ],
        telemetry=TelemetryReference(
            source_id=snapshot.source_id,
            source_sha256=snapshot.source_sha256,
            acquisition=snapshot.acquisition,
            snapshot_sha256=digest(snapshot.model_dump(mode="json")),
            query=snapshot.query,
            evidence_ids=[r.evidence_id for r in rows],
        ),
    )


class HTTPTelemetryTool:
    def __init__(self, settings, audit):
        self.settings, self.audit = settings, audit

    def collect(self, query: TelemetryQuery) -> TelemetrySnapshot:
        request = query.model_dump(mode="json")
        started = time.monotonic()
        event = {
            "event": "collect_telemetry",
            "endpoint": self.settings.url,
            "input_sha256": digest(request),
            "started_at": datetime.now(UTC).isoformat(),
            "status": "failed",
        }
        try:
            with httpx.Client(
                timeout=self.settings.timeout_seconds, follow_redirects=False
            ) as client:
                # Limite esplicito: il contesto dell'LLM non deve caricare un export illimitato.
                with client.stream(
                    "POST", self.settings.url, json=request, headers=self.settings.headers()
                ) as response:
                    response.raise_for_status()
                    body = bytearray()
                    for chunk in response.iter_bytes():
                        body.extend(chunk)
                        if len(body) > 1_000_000:
                            raise ValueError("Telemetry response too large")
            result = TelemetrySnapshot.model_validate_json(bytes(body))
            if (
                result.query != query
                or result.request_sha256 != digest(request)
                or result.source_id != self.settings.source_id
                or result.acquisition != self.settings.acquisition
            ):
                raise ValueError("Telemetry response does not match source/query")
            event.update(status="validated", response_sha256=digest(result.model_dump(mode="json")))
            return result
        except (httpx.HTTPError, ValueError) as error:
            event["error_type"] = type(error).__name__
            raise RuntimeError(f"Telemetry collection failed ({type(error).__name__})") from None
        finally:
            event["elapsed_seconds"] = round(time.monotonic() - started, 6)
            self.audit(event)
