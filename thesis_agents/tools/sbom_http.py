"""Ingresso remoto per Countermeasure: HTTP, senza leggere SBOM dal client."""

import time
from datetime import UTC, datetime
from typing import Literal

import httpx
from pydantic import BaseModel, ConfigDict

from thesis_agents.mcp.client import digest
from thesis_agents.mcp.settings import MCPSettings
from thesis_agents.schemas.base import Identifier
from thesis_agents.schemas.supply_chain import SupplyChainQuery, SupplyChainSnapshot
from thesis_agents.schemas.telemetry_source import SHA256

MAX_RESPONSE_BYTES = 8 * 1024 * 1024


class NoSupplyChainSource(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    transport: Literal["disabled"] = "disabled"


class SupplyChainHTTPSettings(MCPSettings):
    # Riusa URL/timeout/header. Questo trasporto è HTTP applicativo, non MCP.
    transport: Literal["http"] = "http"
    expected_kind: Literal["live", "mock"]
    source_id: Identifier
    sbom_kind: Literal["demo", "provided"]
    sbom_sha256: SHA256 | None = None


class HTTPSupplyChainTool:
    def __init__(self, settings: SupplyChainHTTPSettings, audit):
        self.settings, self.audit = settings, audit

    def collect(self, query: SupplyChainQuery) -> SupplyChainSnapshot:
        request = query.model_dump(mode="json")
        started = time.monotonic()
        event = {
            "event": "collect_supply_chain",
            "endpoint": self.settings.url,
            "started_at": datetime.now(UTC).isoformat(),
            "input_sha256": digest(request),
            "status": "failed",
        }
        try:
            with httpx.Client(
                timeout=self.settings.timeout_seconds, follow_redirects=False
            ) as http:
                with http.stream(
                    "POST", self.settings.url, json=request, headers=self.settings.headers()
                ) as response:
                    response.raise_for_status()
                    body = bytearray()
                    for chunk in response.iter_bytes():
                        body.extend(chunk)
                        if len(body) > MAX_RESPONSE_BYTES:
                            raise ValueError("Supply chain response exceeds limit")
            result = SupplyChainSnapshot.model_validate_json(bytes(body))
            if (
                result.query != query
                or result.source_id != self.settings.source_id
                or result.sbom_kind != self.settings.sbom_kind
                or result.osv_kind != self.settings.expected_kind
                or (self.settings.sbom_sha256 and result.source_sha256 != self.settings.sbom_sha256)
            ):
                raise ValueError("Supply chain response differs from configured source/query")
            event.update(status="validated", response_sha256=digest(result.model_dump(mode="json")))
            return result
        except (httpx.HTTPError, ValueError) as error:
            event["error_type"] = type(error).__name__
            raise RuntimeError(f"Supply chain collection failed ({type(error).__name__})") from None
        finally:
            event["elapsed_seconds"] = round(time.monotonic() - started, 6)
            self.audit(event)
