"""Configurazione HTTP esplicita: nessun comando o script da avviare."""

import os
from typing import Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator


class MCPSettings(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    transport: Literal["mcp"] = "mcp"
    url: str
    expected_kind: Literal["mock", "real"]
    timeout_seconds: float = Field(default=15, gt=0, le=300, allow_inf_nan=False)
    token_env: str | None = Field(default=None, pattern=r"^[A-Za-z_][A-Za-z0-9_]*$")

    @field_validator("url")
    @classmethod
    def http_endpoint(cls, value: str) -> str:
        parsed = urlsplit(value)
        if (
            parsed.scheme not in ("http", "https")
            or not parsed.hostname
            or parsed.username is not None
            or parsed.password is not None
            or parsed.query
            or parsed.fragment
        ):
            raise ValueError("MCP richiede un URL HTTP(S) senza credenziali, query o fragment")
        # Verifica anche l'intervallo della porta prima di aprire una connessione.
        _ = parsed.port
        return value

    def headers(self) -> dict[str, str]:
        if not self.token_env:
            return {}
        token = os.getenv(self.token_env, "").strip()
        if not token:
            raise ValueError(f"Credenziale MCP mancante: {self.token_env}")
        return {"Authorization": f"Bearer {token}"}
