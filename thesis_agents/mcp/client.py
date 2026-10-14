"""Client Streamable HTTP con ciclo di vita compatibile con i tool sincroni CAMEL.

Il portal mantiene il loop di rete in un thread separato. Il context manager
MCP viene aperto e chiuso nello stesso task tramite wrap_async_context_manager;
non si riutilizzano sessioni fra diversi asyncio.run(). Nessun server è avviato
dal client e non sono previsti retry automatici o fallback verso mock locali.
"""

import hashlib
import json
import time
from collections.abc import Callable
from contextlib import ExitStack, asynccontextmanager, suppress
from datetime import UTC, datetime, timedelta
from typing import TypeVar
from uuid import uuid4

import anyio
import httpx
from anyio.from_thread import start_blocking_portal
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client
from mcp.types import CallToolResult

from thesis_agents.mcp.settings import MCPSettings

T = TypeVar("T")


class MCPError(RuntimeError):
    """Errore di trasporto/contratto: non è un esito di lookup unsupported."""


def digest(value) -> str:
    """SHA-256 del JSON UTF-8, chiavi ordinate, compatto, senza NaN/Infinity."""
    data = json.dumps(
        value, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False
    ).encode("utf-8")
    return hashlib.sha256(data).hexdigest()


def schema_shape(schema):
    """Confronto conservativo del contratto v1, ignorando soltanto annotazioni."""
    if isinstance(schema, list):
        return [schema_shape(item) for item in schema]
    if not isinstance(schema, dict):
        return schema
    return {
        key: (
            {name: schema_shape(value) for name, value in item.items()}
            if key in ("properties", "$defs")
            else schema_shape(item)
        )
        for key, item in schema.items()
        if key not in ("title", "description")
    }


def decode_result(result: CallToolResult) -> dict:
    if result.isError:
        raise MCPError("Il tool MCP ha restituito isError=true")
    if result.structuredContent is not None:
        payload = result.structuredContent
    else:
        if len(result.content) != 1 or result.content[0].type != "text":
            raise MCPError("Risposta MCP priva di un unico oggetto JSON")
        try:
            payload = json.loads(result.content[0].text)
        except ValueError:
            raise MCPError("Risposta MCP con JSON non valido") from None
    if not isinstance(payload, dict) or payload.get("ok") is False:
        raise MCPError("Risposta MCP non valida o errore applicativo ok=false")
    return payload


class MCPClient:
    def __init__(self, settings: MCPSettings, *, contracts: dict, audit: Callable | None = None):
        self.settings = settings
        # name -> (input JSON Schema, output JSON Schema). Nessuna discovery libera
        # di nuovi poteri dell'agente: si usano soltanto i contratti configurati.
        self.contracts = contracts
        self.audit = audit or (lambda event: None)
        self._stack = None
        self._session = None
        self._portal = None
        self.server_info = None

    def __enter__(self):
        if self._stack is not None:
            raise MCPError("Client MCP già connesso")
        stack = ExitStack()
        try:
            headers = self.settings.headers()
            self._portal = stack.enter_context(start_blocking_portal())
            self._session = stack.enter_context(
                self._portal.wrap_async_context_manager(self._connect(headers))
            )
            self._stack = stack
            self.audit(
                {
                    "event": "connected",
                    "at": datetime.now(UTC).isoformat(),
                    "endpoint": self.settings.url,
                    "server": self.server_info,
                    "expected_kind": self.settings.expected_kind,
                }
            )
            return self
        except BaseException as exc:
            # Un errore secondario di teardown non deve nascondere il primo errore.
            with suppress(Exception):
                stack.close()
            self._stack = self._session = self._portal = None
            if not isinstance(exc, Exception):
                raise
            self.audit(
                {
                    "event": "connection_failed",
                    "at": datetime.now(UTC).isoformat(),
                    "error_type": type(exc).__name__,
                    "endpoint": self.settings.url,
                }
            )
            # Gli errori del trasporto possono includere URL/risposte esterne.
            # Al modello non inoltriamo traceback o contenuti arbitrari del server.
            raise MCPError("Connessione MCP o discovery dei contratti fallita") from None

    def __exit__(self, *exc):
        try:
            if self._stack:
                self._stack.close()
        except Exception as error:
            self.audit(
                {
                    "event": "close_failed",
                    "error_type": type(error).__name__,
                    "at": datetime.now(UTC).isoformat(),
                }
            )
            if not exc or exc[0] is None:
                raise MCPError("Chiusura della connessione MCP fallita") from None
        finally:
            self._stack = self._session = self._portal = None

    @asynccontextmanager
    async def _connect(self, headers):
        timeout = self.settings.timeout_seconds
        async with httpx.AsyncClient(
            headers=headers, timeout=timeout, follow_redirects=False
        ) as http:
            async with streamable_http_client(self.settings.url, http_client=http) as streams:
                async with ClientSession(
                    streams[0], streams[1], read_timeout_seconds=timedelta(seconds=timeout)
                ) as session:
                    with anyio.fail_after(timeout):
                        info = await session.initialize()
                        self.server_info = {
                            "name": info.serverInfo.name,
                            "version": info.serverInfo.version,
                            "protocol": info.protocolVersion,
                        }
                        tools, cursor, seen = {}, None, set()
                        while True:
                            page = await session.list_tools(cursor=cursor)
                            for tool in page.tools:
                                if tool.name in tools:
                                    raise MCPError("Tool duplicato nel catalogo MCP")
                                tools[tool.name] = tool
                            cursor = page.nextCursor
                            if not cursor:
                                break
                            if cursor in seen:
                                raise MCPError("Paginazione MCP ciclica")
                            seen.add(cursor)
                        for name, (expected_input, expected_output) in self.contracts.items():
                            if name not in tools:
                                raise MCPError("Tool MCP richiesto assente")
                            actual_input = dict(tools[name].inputSchema)
                            # FastMCP omette questo vincolo al livello degli argomenti;
                            # i nostri argomenti sono comunque validati localmente.
                            actual_input.setdefault("additionalProperties", False)
                            if schema_shape(actual_input) != schema_shape(
                                expected_input
                            ) or schema_shape(tools[name].outputSchema) != schema_shape(
                                expected_output
                            ):
                                raise MCPError("Schema MCP incompatibile con il contratto v1")
                    yield session

    async def _invoke(self, name, arguments, call_id):
        with anyio.fail_after(self.settings.timeout_seconds):
            return await self._session.call_tool(name, arguments, meta={"call_id": call_id})

    def call_tool(self, name: str, arguments: dict, parse: Callable[[dict], T]) -> T:
        if self._session is None or name not in self.contracts:
            raise MCPError("Client non connesso o tool non autorizzato")
        started = time.monotonic()
        event = {
            "event": "tool_call",
            "call_id": f"call-{uuid4().hex}",
            "tool": name,
            "endpoint": self.settings.url,
            "expected_kind": self.settings.expected_kind,
            "started_at": datetime.now(UTC).isoformat(),
            "input_sha256": digest(arguments),
        }
        try:
            result = self._portal.call(self._invoke, name, arguments, event["call_id"])
            event["response_sha256"] = digest(result.model_dump(mode="json"))
            payload = decode_result(result)
            parsed = parse(payload)
            event["response_metadata"] = {
                key: payload[key]
                for key in ("contract", "backend_kind", "backend")
                if key in payload
            }
            event["status"] = "validated"
            return parsed
        except Exception as exc:
            event.update(status="failed", error_type=type(exc).__name__)
            # Dopo un timeout il task di trasporto può essere già fallito. Chiudi
            # anche le risorse residue; un retry richiede una nuova connessione.
            self.__exit__(type(exc), exc, exc.__traceback__)
            raise MCPError(f"Chiamata MCP {name} fallita ({type(exc).__name__})") from None
        except BaseException as exc:
            event.update(status="interrupted", error_type=type(exc).__name__)
            self.__exit__(type(exc), exc, exc.__traceback__)
            raise
        finally:
            event.update(
                ended_at=datetime.now(UTC).isoformat(),
                elapsed_seconds=round(time.monotonic() - started, 6),
            )
            self.audit(event)
