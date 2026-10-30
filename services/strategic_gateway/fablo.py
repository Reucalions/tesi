"""Client Fablo REST configurato per le route effettive della baseline locale."""

import os
from typing import Literal
from urllib.parse import quote

import httpx
from pydantic import BaseModel, ConfigDict, Field, SecretStr, field_validator

from thesis_agents.mcp.settings import MCPSettings
from thesis_agents.schemas.base import Text


class FabloSettings(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    url: str
    channel: Text = "my-channel"
    argumentation_chaincode: Text = "argumentation"
    semantic_chaincode: Text = "user-registry"
    provenance_chaincode: Text = "thesis-provenance"
    user: Text = "admin"
    secret_env: str = Field(pattern=r"^[A-Za-z_][A-Za-z0-9_]*$")
    invoke_path: str = "/invoke/{channel}/{chaincode}"
    query_path: str = "/query/{channel}/{chaincode}"
    timeout_seconds: float = Field(default=300, gt=0, le=300, allow_inf_nan=False)

    @field_validator("url")
    @classmethod
    def endpoint(cls, value):
        return MCPSettings.http_endpoint(value).rstrip("/")

    @field_validator("invoke_path", "query_path")
    @classmethod
    def route(cls, value):
        if (
            not value.startswith("/")
            or value.startswith("//")
            or "?" in value
            or "#" in value
            or "{channel}" not in value
            or "{chaincode}" not in value
        ):
            raise ValueError("Fablo routes require channel and chaincode placeholders")
        value.format(channel="channel", chaincode="chaincode")
        return value


class FabloError(RuntimeError):
    pass


class FabloClient:
    def __init__(self, settings: FabloSettings, *, transport=None):
        self.settings = settings
        self.http = httpx.Client(
            base_url=settings.url,
            timeout=settings.timeout_seconds,
            follow_redirects=False,
            transport=transport,
        )
        self._token: SecretStr | None = None

    def close(self):
        self.http.close()

    def _post(self, path, body, *, authenticated=True):
        try:
            headers = (
                {"Authorization": f"Bearer {self._token.get_secret_value()}"}
                if authenticated and self._token
                else {}
            )
            response = self.http.post(path, json=body, headers=headers)
            # 202 non viene trattato come una transazione completata.
            if response.status_code != 200:
                raise FabloError(f"Fablo HTTP {response.status_code}; operation not verified")
            data = response.json()
        except (httpx.HTTPError, ValueError):
            raise FabloError("Fablo transport or JSON response failed") from None
        if not isinstance(data, dict):
            raise FabloError("Fablo requires a JSON object response")
        return data

    def enroll(self):
        secret = os.environ.get(self.settings.secret_env, "")
        if not secret:
            raise FabloError(f"Missing Fablo credential environment: {self.settings.secret_env}")
        result = self._post(
            "/user/enroll", {"id": self.settings.user, "secret": secret}, authenticated=False
        )
        if not isinstance(result.get("token"), str) or not result["token"]:
            raise FabloError("Fablo enrollment did not return a token")
        self._token = SecretStr(result["token"])

    def call(
        self,
        kind: Literal["invoke", "query"],
        chaincode,
        method,
        args,
        *,
        transient=None,
        allow_missing=False,
    ):
        if kind not in ("invoke", "query"):
            raise ValueError("Unknown Fablo operation")
        if self._token is None:
            self.enroll()
        template = self.settings.invoke_path if kind == "invoke" else self.settings.query_path
        path = template.format(
            channel=quote(self.settings.channel, safe=""), chaincode=quote(chaincode, safe="")
        )
        body = {"method": method, "args": args}
        if transient is not None:
            body["transient"] = transient
        response = self._post(path, body)
        payload = response.get("response")
        if not isinstance(payload, dict):
            raise FabloError("Fablo response envelope is missing")
        if allow_missing and kind == "query" and payload == {"error": "NOT_FOUND"}:
            return payload
        if "error" in payload or any(key.lower().startswith("errore") for key in payload):
            raise FabloError("Chaincode reported an application error")
        return payload
