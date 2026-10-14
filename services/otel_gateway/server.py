"""Gateway HTTP read-only sugli export NDJSON del Collector della baseline.

Non avvia la pipeline LLM del repository esterno e non modifica i suoi file.
Riconosce identità dichiarate in attributi espliciti e self-log del Collector;
righe YAML, immagini dichiarate e testo libero non provano un software in esecuzione.
"""

import argparse
import hashlib
import json
import os
import socket
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

from thesis_agents.mcp.client import digest
from thesis_agents.schemas.telemetry_source import (
    TelemetryObservation,
    TelemetryQuery,
    TelemetrySnapshot,
    unix_nano,
)

MAX_FILE_BYTES = 16 * 1024 * 1024


def attributes(items):
    result = {}
    for item in items:
        key, value = item["key"], item["value"]
        if key in result:
            raise ValueError("Duplicate OTEL attribute")
        if "stringValue" in value:
            result[key] = value["stringValue"]
        elif "boolValue" in value:
            result[key] = value["boolValue"]
    return result


def identify(resource, record):
    attrs = attributes(resource.get("attributes", []))
    if all(
        key in attrs
        for key in (
            "service.name",
            "service.instance.id",
            "thesis.software.name",
            "thesis.software.version",
        )
    ):
        return {
            "service_name": attrs["service.name"],
            "service_instance_id": attrs["service.instance.id"],
            "package": attrs["thesis.software.name"],
            "version": attrs["thesis.software.version"],
            "identity_basis": "explicit-resource-attributes",
            "endpoint_exposed": attrs.get("thesis.endpoint.exposed"),
            "deserialization_observed": attributes(record.get("attributes", [])).get(
                "thesis.deserialization.observed"
            ),
        }
    body = record.get("body", {}).get("stringValue", "")
    # La baseline contiene log strutturati del Collector: il JSON della risorsa
    # è nel body, non negli attributi OTEL esterni (che descrivono solo l'host).
    start = body.find("{")
    if start < 0:
        return None
    try:
        value = json.loads(body[start:])
    except ValueError:
        return None
    if not isinstance(value, dict):
        return None
    identity = value.get("resource", {})
    if (
        not isinstance(identity, dict)
        or identity.get("service.name") != "otelcol-contrib"
        or not value.get("otelcol.component.id")
        or not value.get("otelcol.signal")
        or not identity.get("service.version")
        or not identity.get("service.instance.id")
    ):
        return None
    return {
        "service_name": "otelcol-contrib",
        "package": "otelcol-contrib",
        "service_instance_id": identity["service.instance.id"],
        "version": identity["service.version"],
        "identity_basis": "collector-self-log",
    }


def read_snapshot(path: Path, query: TelemetryQuery, *, source_id, acquisition):
    with path.open("rb") as stream:
        before = os.fstat(stream.fileno())
        raw = stream.read(MAX_FILE_BYTES + 1)
        after = os.fstat(stream.fileno())
        current = path.stat()
    if len(raw) > MAX_FILE_BYTES:
        raise ValueError("Export exceeds 16 MiB; rotate or partition it before querying")
    # Controlla sia il descrittore letto sia il percorso: una rotazione può
    # sostituire il file senza modificare il descrittore già aperto.
    signatures = {
        (stat.st_dev, stat.st_ino, stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns)
        for stat in (before, after, current)
    }
    if len(signatures) != 1:
        raise ValueError("Export changed while reading; retry on a stable snapshot")
    rows, total, recognized = [], 0, 0
    for line_number, line in enumerate(raw.splitlines(), 1):
        if not line.strip():
            continue
        document = json.loads(line)
        if "resourceLogs" not in document:
            raise ValueError("Expected OTEL resourceLogs NDJSON")
        for ri, resource_logs in enumerate(document["resourceLogs"]):
            resource = resource_logs.get("resource", {})
            for si, scope_logs in enumerate(resource_logs.get("scopeLogs", [])):
                for li, record in enumerate(scope_logs.get("logRecords", [])):
                    total += 1
                    identity = identify(resource, record)
                    if identity is None:
                        continue
                    observed = int(record.get("observedTimeUnixNano", 0))
                    if observed <= 0:
                        continue
                    recognized += 1
                    if (
                        identity["service_name"],
                        identity["service_instance_id"],
                        identity["package"],
                    ) != (
                        query.service_name,
                        query.service_instance_id,
                        query.package_name,
                    ) or not unix_nano(query.start_time) <= observed < unix_nano(query.end_time):
                        continue
                    pointer = f"/resourceLogs/{ri}/scopeLogs/{si}/logRecords/{li}"
                    fingerprint = digest({"resource": resource, "record": record})
                    row = TelemetryObservation(
                        evidence_id="otel:"
                        + digest(
                            {"line": line_number, "pointer": pointer, "record_sha256": fingerprint}
                        )[:24],
                        observed_time_unix_nano=observed,
                        line=line_number,
                        pointer=pointer,
                        record_sha256=fingerprint,
                        **identity,
                    )
                    rows.append(row)
                    if len(rows) > 100:
                        raise ValueError("More than 100 observations; narrow the query window")
    return TelemetrySnapshot(
        source_id=source_id,
        source_sha256=hashlib.sha256(raw).hexdigest(),
        source_size_bytes=len(raw),
        acquisition=acquisition,
        acquired_at=datetime.now(UTC),
        query=query,
        request_sha256=digest(query.model_dump(mode="json")),
        file_record_count=total,
        recognized_record_count=recognized,
        observations=rows,
    )


def handler_for(path, source_id, acquisition):
    class Handler(BaseHTTPRequestHandler):
        def send_json(self, status, payload):
            content = json.dumps(payload, ensure_ascii=False).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(content)))
            self.end_headers()
            self.wfile.write(content)

        def do_GET(self):
            if self.path == "/health":
                self.send_json(200, {"backend": "otel-file-gateway-v1"})
            else:
                self.send_json(404, {"error": "not_found"})

        def do_POST(self):
            if self.path != "/v1/observations":
                self.send_json(404, {"error": "not_found"})
                return
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if not 0 < length <= 8192:
                    raise ValueError("Invalid request length")
                query = TelemetryQuery.model_validate_json(self.rfile.read(length))
                result = read_snapshot(path, query, source_id=source_id, acquisition=acquisition)
            except (ValueError, OSError, KeyError, TypeError, AttributeError):
                # Il client non riceve percorsi filesystem o frammenti di log.
                self.send_json(422, {"error": "invalid_query_or_export"})
                return
            self.send_json(200, result.model_dump(mode="json"))

    return Handler


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--file", type=Path, required=True)
    parser.add_argument("--source-id", required=True)
    parser.add_argument(
        "--acquisition", choices=("recorded", "collector-file", "sdk-file"), default="recorded"
    )
    parser.add_argument("--port", type=int, default=8004)
    parser.add_argument("--fd", type=int, help="Socket riservato dal runner di test")
    args = parser.parse_args()
    if not args.file.is_file():
        parser.error("Export file not found")
    server = ThreadingHTTPServer(
        ("127.0.0.1", args.port),
        handler_for(args.file, args.source_id, args.acquisition),
        bind_and_activate=args.fd is None,
    )
    if args.fd is not None:
        server.socket.close()
        server.socket = socket.socket(fileno=args.fd)
        server.server_address = server.socket.getsockname()
    with server:
        server.serve_forever()


if __name__ == "__main__":
    main()
