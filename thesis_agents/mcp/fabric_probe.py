"""Collaudo MCP nativo isolato: non esegue la Workforce e non seleziona mitigazioni."""

import argparse
import json
from pathlib import Path

from thesis_agents.mcp.client import MCPClient, digest
from thesis_agents.mcp.fabric_client import native_call
from thesis_agents.mcp.fabric_contracts import (
    NativeGraph,
    fabric_contracts,
)
from thesis_agents.mcp.settings import MCPSettings


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://127.0.0.1:8008/mcp")
    parser.add_argument("--graph", required=True, type=Path)
    parser.add_argument("--ontology", required=True, type=Path)
    parser.add_argument("--resource", required=True)
    parser.add_argument("--request", required=True)
    parser.add_argument("--provenance", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    graph = NativeGraph.model_validate_json(args.graph.read_text()).model_dump(
        mode="json", by_alias=True
    )
    ontology = args.ontology.read_text()
    record = json.loads(args.provenance.read_text())
    # L'ontologia e i due individui determinano la chiave di analisi, separata
    # dai nomi TBox condivisi e quindi riutilizzabile senza collisioni tra casi.
    ontology_key = "analysis:" + digest(
        {
            "ontology": ontology,
            "resource": args.resource,
            "request": args.request,
        }
    )
    graph_id = "graph:" + digest(graph)
    args.output.mkdir(parents=True, exist_ok=False)
    results = {}

    def save(name, value):
        with (args.output / name).open("x") as stream:
            stream.write(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n")

    save(
        "inputs.json",
        {
            "graph": graph,
            "ontology": ontology,
            "resource": args.resource,
            "request": args.request,
            "record": record,
            "scope": "native-backend-probe-without-workforce-or-LLM",
        },
    )

    def audit(event):
        with (args.output / "mcp_events.jsonl").open("a") as stream:
            stream.write(json.dumps(event) + "\n")

    try:
        with MCPClient(
            MCPSettings(url=args.url, expected_kind="real", timeout_seconds=300),
            contracts=fabric_contracts(),
            audit=audit,
        ) as client:
            operations = [
                ("store_graph", {"graph_id": graph_id, "graph": graph}),
                ("get_graph", {"graph_id": graph_id}),
                ("rank_graph", {"graph_id": graph_id}),
                ("get_rank_result", {"graph_id": graph_id}),
                ("get_annotated_graph", {"graph_id": graph_id}),
                (
                    "analyze_ontology",
                    {
                        "ontology_key": ontology_key,
                        "ontology": ontology,
                        "resource": args.resource,
                        "request": args.request,
                    },
                ),
                ("get_reasoner_result", {"ontology_key": ontology_key}),
                ("record_provenance", {"record": record}),
                ("read_provenance", {"run_id": record["run_id"]}),
            ]
            for operation, arguments in operations:
                response = native_call(client, operation, **arguments).model_dump(mode="json")
                results[operation] = response
                save(operation + ".json", response)
        save(
            "summary.json",
            {
                "passed": True,
                "operations": list(results),
                "verification": "peer-readback; no independent block proof",
                "workforce_mapping": "not_assessed",
            },
        )
    except Exception as exc:
        save(
            "summary.json",
            {"passed": False, "operations": list(results), "error_type": type(exc).__name__},
        )
        raise


if __name__ == "__main__":
    main()
