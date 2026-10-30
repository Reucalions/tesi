"""Chiamata MCP nativa vincolata a operazione, richiesta e tipo di backend."""

from thesis_agents.mcp.client import digest
from thesis_agents.mcp.fabric_contracts import FABRIC_TOOLS, FabricResponse


def native_call(client, operation, **arguments):
    request = FABRIC_TOOLS[operation].model_validate(arguments)
    payload = request.model_dump(mode="json", by_alias=True)

    def parse(value):
        result = FabricResponse.model_validate(value)
        if (
            client.settings.expected_kind != "real"
            or result.operation != operation
            or result.request_sha256 != digest(payload)
        ):
            raise ValueError("Native Fabric response does not match the requested operation")
        return result

    return client.call_tool(operation, payload, parse)
