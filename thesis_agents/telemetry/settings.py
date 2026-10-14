"""Selezione dell'ingresso statico o di un servizio HTTP già in esecuzione."""

from typing import Literal

from pydantic import BaseModel, ConfigDict

from thesis_agents.mcp.settings import MCPSettings
from thesis_agents.schemas.base import Identifier


class StaticSource(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    transport: Literal["static"] = "static"


class TelemetryHTTPSettings(MCPSettings):
    # Riusa solo validazione URL, timeout e header; il client non parla MCP.
    transport: Literal["http"] = "http"
    expected_kind: Literal["otel-file-gateway-v1"] = "otel-file-gateway-v1"
    source_id: Identifier
    acquisition: Literal["recorded", "collector-file", "sdk-file"]
