"""API OSV sintetica per prove HTTP offline; non fa richieste a Internet."""

import argparse
import json
import socket
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fd", type=int, required=True)
    parser.add_argument("--replies", type=Path, required=True)
    parser.add_argument("--requests", type=Path, required=True)
    args = parser.parse_args()

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            self.send_response(200)
            self.end_headers()

        def do_POST(self):
            query = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
            with args.requests.open("a") as stream:
                stream.write(json.dumps(query) + "\n")
            fixture = json.loads(args.replies.read_text())
            token = query.get("page_token")
            index = int(token.removeprefix("page-")) if token else 0
            body = json.dumps(fixture["pages"][index]).encode()
            self.send_response(fixture.get("status", 200))
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler, bind_and_activate=False)
    server.socket.close()
    server.socket = socket.socket(fileno=args.fd)
    server.server_address = server.socket.getsockname()
    with server:
        server.serve_forever()


if __name__ == "__main__":
    main()
