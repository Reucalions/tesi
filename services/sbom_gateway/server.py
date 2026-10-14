"""Gateway separato: SBOM CycloneDX + query OSV per il componente Maven associato.

La SBOM e l'associazione all'asset sono configurate dall'operatore, mai dall'LLM.
Il server non genera strategie e non modifica il report CTI o i repository esterni.
"""

import argparse
import hashlib
import json
import socket
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit

import httpx

from thesis_agents.mcp.client import digest
from thesis_agents.schemas.supply_chain import (
    OSV_URL,
    AssetBinding,
    OSVExchange,
    OSVResponse,
    SupplyChainQuery,
    SupplyChainSnapshot,
    select_component,
)
from thesis_agents.tools.sbom_http import MAX_RESPONSE_BYTES


def query_osv(query, url, http):
    """Completa la paginazione o fallisce: nessun risultato parziale accettato."""
    pages, tokens = [], set()
    request = query
    for _ in range(10):
        with http.stream("POST", url, json=request) as response:
            response.raise_for_status()
            body = bytearray()
            for chunk in response.iter_bytes():
                body.extend(chunk)
                if len(body) > 2 * 1024 * 1024:
                    raise ValueError("OSV page exceeds limit")
        raw = json.loads(body)
        parsed = OSVResponse.model_validate(raw)
        pages.append(OSVExchange(request=request, response=raw))
        token = parsed.next_page_token
        if not token:
            return pages
        if token in tokens:
            raise ValueError("OSV repeated pagination token")
        tokens.add(token)
        request = query | {"page_token": token}
    raise ValueError("OSV pagination exceeds prototype limit")


class Gateway:
    def __init__(self, sbom: Path, binding: AssetBinding, source_id, sbom_kind, osv_kind, osv_url):
        # Legge una copia fissa all'avvio: nessun file modificato a metà run.
        with sbom.open("rb") as stream:
            raw = stream.read(1024 * 1024 + 1)
        if len(raw) > 1024 * 1024:
            raise ValueError("SBOM exceeds 1 MiB")
        self.document = json.loads(raw)
        if not isinstance(self.document, dict):
            raise ValueError("SBOM must be a JSON object")
        self.source_sha256 = hashlib.sha256(raw).hexdigest()
        self.binding, self.source_id, self.sbom_kind = binding, source_id, sbom_kind
        self.osv_kind, self.osv_url = osv_kind, osv_url
        parsed = urlsplit(osv_url)
        if osv_kind == "live" and osv_url != OSV_URL:
            raise ValueError("Live OSV requires the official endpoint")
        if osv_kind == "mock" and not (
            parsed.scheme == "http"
            and parsed.hostname in ("127.0.0.1", "localhost", "::1")
            and not parsed.username
            and not parsed.password
            and not parsed.query
            and not parsed.fragment
        ):
            raise ValueError("Mock OSV requires an explicit loopback HTTP endpoint")

    def assess(self, query: SupplyChainQuery, http):
        component = select_component(self.document, self.binding, query)
        pages = query_osv(component.osv_query(), self.osv_url, http)
        return SupplyChainSnapshot(
            source_id=self.source_id,
            sbom_kind=self.sbom_kind,
            osv_kind=self.osv_kind,
            osv_url=self.osv_url,
            acquired_at=datetime.now(UTC),
            query=query,
            request_sha256=digest(query.model_dump(mode="json")),
            binding=self.binding,
            source_sha256=self.source_sha256,
            document_sha256=digest(self.document),
            document=self.document,
            pages=pages,
        )


def handler_for(gateway):
    class Handler(BaseHTTPRequestHandler):
        def send_json(self, status, data):
            body = json.dumps(data, ensure_ascii=False).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if self.path == "/health":
                self.send_json(200, {"backend": "sbom-osv-http-v1", "osv_kind": gateway.osv_kind})
            else:
                self.send_json(404, {"error": "not_found"})

        def do_POST(self):
            if self.path != "/v1/enrichment":
                self.send_json(404, {"error": "not_found"})
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 8192:
                    raise ValueError("Invalid request length")
                query = SupplyChainQuery.model_validate_json(self.rfile.read(length))
                with httpx.Client(timeout=25, follow_redirects=False) as http:
                    result = gateway.assess(query, http).model_dump(mode="json")
                if len(json.dumps(result, ensure_ascii=False).encode()) > MAX_RESPONSE_BYTES:
                    raise ValueError("Snapshot exceeds limit")
            except httpx.HTTPError:
                self.send_json(502, {"error": "osv_unavailable"})
                return
            except (ValueError, KeyError, TypeError, AttributeError):
                self.send_json(422, {"error": "invalid_query_or_source"})
                return
            self.send_json(200, result)

    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sbom", type=Path, required=True)
    parser.add_argument("--source-id", required=True)
    parser.add_argument("--sbom-kind", choices=("demo", "provided"), required=True)
    parser.add_argument("--service-name", required=True)
    parser.add_argument("--runtime-package", required=True)
    parser.add_argument("--component-ref", required=True)
    parser.add_argument("--osv-kind", choices=("live", "mock"), default="live")
    parser.add_argument("--osv-url", default=OSV_URL)
    parser.add_argument("--port", type=int, default=8005)
    parser.add_argument("--fd", type=int, help="Socket riservato dai test")
    args = parser.parse_args()
    gateway = Gateway(
        args.sbom,
        AssetBinding(
            service_name=args.service_name,
            runtime_package=args.runtime_package,
            component_ref=args.component_ref,
        ),
        args.source_id,
        args.sbom_kind,
        args.osv_kind,
        args.osv_url,
    )
    server = ThreadingHTTPServer(
        ("127.0.0.1", args.port), handler_for(gateway), bind_and_activate=args.fd is None
    )
    if args.fd is not None:
        server.socket.close()
        server.socket = socket.socket(fileno=args.fd)
        server.server_address = server.socket.getsockname()
    with server:
        server.serve_forever()


if __name__ == "__main__":
    main()
