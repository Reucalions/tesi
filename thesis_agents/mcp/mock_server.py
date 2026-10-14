"""Server mock avviabile separatamente: python -m thesis_agents.mcp.mock_server."""

import argparse

from mcp.server.fastmcp import FastMCP
from mcp.types import ToolAnnotations

from thesis_agents.mcp.contracts import LOOKUP_CONTRACT, LookupResponse
from thesis_agents.schemas import SoftwareObservation
from thesis_agents.tools.vulnerability_mock import MockVulnerabilityTool


def create_server(*, host: str = "127.0.0.1", port: int = 8001) -> FastMCP:
    server = FastMCP(
        "thesis-vulnerability-mock", host=host, port=port, json_response=True, log_level="WARNING"
    )
    backend = MockVulnerabilityTool()

    @server.tool(annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True))
    def lookup_vulnerabilities(software: SoftwareObservation) -> LookupResponse:
        """Lookup a software observation using an illustrative fixture, not a live KG."""
        return LookupResponse(
            contract=LOOKUP_CONTRACT,
            backend_kind="mock",
            backend="local-log4j-fixture-v1",
            result=backend.lookup_vulnerabilities(software),
        )

    return server


def main(argv=None):
    parser = argparse.ArgumentParser(description="Server MCP HTTP del lookup mock")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8001)
    args = parser.parse_args(argv)
    if not 1 <= args.port <= 65535:
        parser.error("La porta deve essere compresa fra 1 e 65535")
    create_server(host=args.host, port=args.port).run(transport="streamable-http")


if __name__ == "__main__":
    main()
