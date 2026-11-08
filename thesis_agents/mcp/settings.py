"""Trasporti MCP configurati dall'operatore, prima dell'avvio degli agenti."""

import os
from pathlib import Path
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

    @property
    def endpoint(self) -> str:
        return self.url


class MCPStdioSettings(BaseModel):
    """Processo senza shell; le credenziali sono riferimenti a variabili ambiente."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    transport: Literal["mcp-stdio"] = "mcp-stdio"
    command: str = Field(min_length=1)
    args: tuple[str, ...] = ()
    cwd: str | None = None
    env_from: dict[str, str] = Field(default_factory=dict)
    expected_kind: Literal["mock", "real"]
    timeout_seconds: float = Field(default=120, gt=0, le=300, allow_inf_nan=False)

    @field_validator("command")
    @classmethod
    def executable(cls, value: str) -> str:
        if not value.strip() or "\x00" in value:
            raise ValueError("MCP stdio richiede un eseguibile, senza shell implicita")
        return value

    @field_validator("args")
    @classmethod
    def arguments(cls, values: tuple[str, ...]) -> tuple[str, ...]:
        if any("\x00" in value for value in values):
            raise ValueError("Argomenti stdio non validi")
        return values

    @field_validator("cwd")
    @classmethod
    def working_directory(cls, value: str | None) -> str | None:
        if value is not None and (not Path(value).is_absolute() or "\x00" in value):
            raise ValueError("cwd stdio deve essere un percorso assoluto")
        return value

    @field_validator("env_from")
    @classmethod
    def environment_names(cls, values: dict[str, str]) -> dict[str, str]:
        import re

        if any(
            not re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]*", name)
            for name in (*values, *values.values())
        ):
            raise ValueError("env_from contiene nomi di variabili non validi")
        return values

    def environment(self) -> dict[str, str]:
        result = {}
        for destination, source in self.env_from.items():
            value = os.getenv(source)
            if not value:
                raise ValueError(f"Variabile MCP stdio mancante: {source}")
            result[destination] = value
        return result

    @property
    def endpoint(self) -> str:
        # Argomenti e valori d'ambiente non entrano negli eventi di audit.
        return f"stdio:{Path(self.command).name}"


MCPConnectionSettings = MCPSettings | MCPStdioSettings
