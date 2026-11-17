"""Measure the existing native ranking through MCP; never implement ranking here.

Prepare freezes inputs/protocol before collection. Collect temporarily selects the
baseline ontology in an identical CCaaS image, then restores the original container.
Analyze reads archived replies only. No SaaS tests, network reset or mutation retry.
"""

from __future__ import annotations

import argparse
import asyncio
import csv
import hashlib
import itertools
import json
import math
import os
import statistics
import subprocess
import time
from collections import Counter
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from uuid import uuid4

ROOT = Path(__file__).resolve().parents[1]
PIPE = Path("/Users/reucalion/Desktop/agent-based-cti-argumentation-pipeline")
LEDGER = Path("/Users/reucalion/Desktop/semantic-cti-ledger-argumentation")
BRIDGE = PIPE / "mcp-fablo-server"
NODE = ROOT / "output/shared-finalization-20261103/runtime/node_modules/node/bin/node"
CONTAINER = "ccaas_peer0.org1.example.com_my-channel_argumentation_1.0"
BASELINE = "/chaincode/onto/client_final_ontology.owl"
IMAGE = "sha256:b1c8b513c99558909128bf8568307af14c7f3f7a7d1490972ac2cf601185e022"
EPS = 1e-6


def read(path):
    return json.loads(path.read_text())


def write(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("x") as stream:
        json.dump(value, stream, indent=2, allow_nan=False)
        stream.write("\n")


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def run(*args):
    return subprocess.check_output(args, text=True).strip()


def utc():
    return datetime.now(UTC).isoformat()


def topology(graph):
    nodes = {n["id"]: n["type"] for n in graph["nodes"]}
    edges = {(e["from"], e["to"]) for e in graph["edges"]}
    if len(nodes) != len(graph["nodes"]) or len(edges) != len(graph["edges"]):
        raise ValueError("Duplicate graph nodes or edges")
    if any(a not in nodes or b not in nodes for a, b in edges):
        raise ValueError("Dangling edge")
    return nodes, edges


def unwrap(raw):
    if raw.get("isError"):
        raise ValueError("MCP error: " + json.dumps(raw["content"])[:700])
    envelope = json.loads(next(c["text"] for c in raw["content"] if c["type"] == "text"))
    if envelope.get("ok") is not True:
        raise ValueError("Tool error: " + json.dumps(envelope)[:700])
    value = envelope["payload"]
    for _ in range(10):
        if isinstance(value, str):
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                return value
        elif isinstance(value, dict) and "error" in value:
            raise ValueError("Backend error: " + json.dumps(value)[:700])
        elif isinstance(value, dict) and "response" in value:
            value = value["response"]
        elif isinstance(value, dict) and "success" in value:
            value = value["success"]
        else:
            return value
    raise ValueError("Unexpected nested response")


def ranking(rows):
    if not isinstance(rows, list) or not rows:
        raise ValueError("Missing ranking is not a determinism proof")
    result = {}
    for row in rows:
        name, score = row["name"], row["score"]
        if not isinstance(name, str) or not name or name in result:
            raise ValueError("Invalid/duplicate candidate name")
        if (
            isinstance(score, bool)
            or not isinstance(score, (int, float))
            or not math.isfinite(score)
        ):
            raise ValueError("Ranking requires finite numeric scores")
        result[name] = score
    return result


def winners(scores):
    maximum = max(scores.values())
    return sorted(k for k, v in scores.items() if maximum - v <= EPS)


def compare(a, b):
    if a.keys() != b.keys() or not a:
        return {"comparable": False, "scores_equal": False, "winner_equal": False}
    delta = max(abs(a[k] - b[k]) for k in a)
    return {
        "comparable": True,
        "scores_equal": delta <= EPS,
        "scores_exact": a == b,
        "max_absolute_delta": delta,
        "winner_equal": winners(a) == winners(b),
    }


def audit(graph, rows, annotated, case):
    scores = ranking(rows)
    expected, edges = topology(graph)
    candidate_names = {n for n, t in expected.items() if t == "strategy"}
    labels = {n["data"]["id"]: n["data"]["label"] for n in annotated["nodes"]}
    if len(labels) != len(annotated["nodes"]) or len(set(labels.values())) != len(labels):
        raise ValueError("Duplicate native node ID/label")
    weights = {}
    id_weights = {}
    for edge in annotated["edges"]:
        d = edge["data"]
        value = d["label"]
        if (
            isinstance(value, bool)
            or not isinstance(value, (int, float))
            or not math.isfinite(value)
        ):
            raise ValueError("Non-finite or missing native relation weight")
        if not -1 <= value <= 1:
            raise ValueError("Relation weight outside [-1,1]")
        pair = (labels[d["source"]], labels[d["target"]])
        if pair in weights:
            raise ValueError("Duplicate native edge")
        weights[pair] = value
        id_weights[(d["source"], d["target"])] = value
    paths = []
    missing = []
    for row in rows:
        explanation = row.get("explanation") or {}
        count = 0
        for category in ["against", "favor"]:
            for proof in explanation.get(category) or []:
                path = proof["path"]
                valid = (
                    len(path) >= 2
                    and all(i in labels for i in path)
                    and labels.get(path[-1]) == row["name"]
                    and all(pair in id_weights for pair in zip(path, path[1:], strict=False))
                )
                product = (
                    math.prod(id_weights[pair] for pair in zip(path, path[1:], strict=False))
                    if valid
                    else None
                )
                reported = proof["strengthProduct"]
                finite = (
                    isinstance(reported, (int, float))
                    and not isinstance(reported, bool)
                    and math.isfinite(reported)
                )
                product_ok = valid and finite and abs(product - reported) <= 1e-5
                sign_ok = finite and (reported < 0 if category == "against" else reported > 0)
                paths.append(
                    {
                        "candidate": row["name"],
                        "category": category,
                        "native_path": path,
                        "label_path": [labels.get(i) for i in path],
                        "reported_product": reported,
                        "computed_product": product,
                        "directed_path_and_product_valid": product_ok,
                        "simple_sign_interpretation_agrees": sign_ok,
                    }
                )
                count += 1
        if count == 0:
            missing.append(row["name"])
    clash = [
        {
            "from": e["from"],
            "to": e["to"],
            "weight": weights.get((e["from"], e["to"])),
            "negative": weights.get((e["from"], e["to"]), 0) < 0,
        }
        for e in case["expected_attack_edges"]
    ]
    structure_ok = (
        set(scores) == candidate_names
        and set(labels.values()) == set(expected)
        and set(weights) == edges
    )
    return {
        "scores": scores,
        "winners_within_1e_6": winners(scores),
        "candidate_and_topology_complete": structure_ok,
        "native_multi_candidate": len(scores) > 1
        and annotated.get("method") != "single_candidate_convention_v1",
        "weights_finite_and_in_range": True,
        "weights_by_label": [
            {"from": a, "to": b, "weight": w} for (a, b), w in sorted(weights.items())
        ],
        "expected_clashes": clash,
        "expected_clashes_negative": all(e["negative"] for e in clash),
        "paths": paths,
        "candidates_without_paths": missing,
        "path_products_valid": all(p["directed_path_and_product_valid"] for p in paths),
        "sign_interpretation_disagreements": sum(
            not p["simple_sign_interpretation_agrees"] for p in paths
        ),
    }


def runtime():
    info = json.loads(run("docker", "inspect", CONTAINER))[0]
    return {
        "observed_utc": utc(),
        "id": info["Id"],
        "image": info["Image"],
        "state": {k: info["State"][k] for k in ["Running", "OOMKilled", "ExitCode", "StartedAt"]},
        "ontology_env": [
            e for e in info["Config"]["Env"] if e.startswith("ARGUMENTATION_ONTOLOGY_PATH=")
        ],
        "network": sorted(info["NetworkSettings"]["Networks"]),
        "sha256": run(
            "docker",
            "exec",
            CONTAINER,
            "sha256sum",
            "/chaincode/bin/chaincode",
            "/chaincode/graph/lib/libgraph.so",
            BASELINE,
            "/chaincode/onto/controlled-logback.owl",
        ),
        "containers": run("docker", "ps", "--format", "{{.ID}} {{.Names}} {{.Status}}"),
        "disk": run("df", "-h", str(ROOT)),
        "memory": run("memory_pressure", "-Q"),
    }


def prepare(out):
    out.mkdir(exist_ok=False)
    catalog = read(ROOT / "config/scientific-graph-cases.v1.json")
    write(out / "scientific-cases.json", catalog)
    repositories = {}
    for repo, branch in [(ROOT, "full"), (PIPE, "costa-thesis"), (LEDGER, "costa-thesis")]:
        actual = run("git", "-C", str(repo), "branch", "--show-current")
        if actual != branch:
            raise ValueError(f"Unexpected branch: {repo}: {actual}")
        repositories[str(repo)] = {
            "branch": actual,
            "head": run("git", "-C", str(repo), "rev-parse", "HEAD"),
        }
    for case in catalog["cases"]:
        graphs = []
        for variant, source in [("original", case["original"]), ("reordered", case["reordered"])]:
            path = LEDGER / source
            if sha(path) != case["sha256"][path.name]:
                raise ValueError(f"Input hash changed: {path}")
            graph = read(path)
            graphs.append(graph)
            write(out / "inputs" / f"{case['id']}-{variant}.json", graph)
        if topology(graphs[0]) != topology(graphs[1]):
            raise ValueError("Reordered graph has changed topology")
    protected = {}
    directories = [
        ROOT / "output/case-improvements-20261106/runs",
        ROOT / "output/case-improvements-20261106/cases",
        ROOT / "output/c4-collaudo-20261112-r1",
        ROOT / "output/c4-collaudo-20261112-r2",
        ROOT / "output/component-metrics-20261112-r1",
        ROOT / "evaluation/annotated-sample-v1",
        ROOT / "evaluation/annotated-sample-v2",
        LEDGER / "fablo-rest/data/decisions",
        PIPE / "mcp-fablo-server/src",
        PIPE / "mcp-fablo-server/build",
        LEDGER / "fablo-rest/src",
        LEDGER / "fablo-rest/dist",
        ROOT / "thesis_agents",
        ROOT / "services",
    ]
    for directory in directories:
        if directory.is_dir():
            for path in directory.rglob("*"):
                if path.is_file() and "__pycache__" not in path.parts:
                    protected[str(path)] = sha(path)
    for pattern in ["docs/materiali/*.docx", "config/scientific-graph-cases.v1.json"]:
        for path in ROOT.glob(pattern):
            protected[str(path)] = sha(path)
    for path in (LEDGER / "chaincode-argumentation").glob("*.go"):
        protected[str(path)] = sha(path)
    for path in (LEDGER / "chaincode-argumentation/client/tests").glob("graph_test_*.json"):
        protected[str(path)] = sha(path)
    write(out / "protected-before.json", protected)
    trials = []
    token = uuid4().hex[:10]
    for repetition in range(1, 4):
        for index, case in enumerate(catalog["cases"], 1):
            variants = (
                ["original", "reordered"]
                if (index + repetition) % 2 == 0
                else ["reordered", "original"]
            )
            for variant in variants:
                name = f"{case['id']}-{variant}-r{repetition}"
                trials.append(
                    {
                        "id": name,
                        "case": case["id"],
                        "variant": variant,
                        "repetition": repetition,
                        "graph_id": f"benchmark-native-{out.name}-{name}-{token}",
                    }
                )
    protocol = {
        "created_utc": utc(),
        "reference_date": "2026-11-12",
        "repositories": repositories,
        "collector_sha256": sha(Path(__file__)),
        "scientific_cases_sha256": sha(out / "scientific-cases.json"),
        "input_sha256": {p.name: sha(p) for p in sorted((out / "inputs").glob("*.json"))},
        "planned_trials": 30,
        "replications_per_input": 3,
        "trials": trials,
        "calls_per_trial": [
            "store_graph",
            "rank_graph",
            "get_graph",
            "get_rank_result",
            "get_annotated_graph",
        ],
        "absolute_score_tolerance": EPS,
        "absolute_path_product_tolerance": 1e-5,
        "winner": "All maximum-score candidates within absolute 1e-6; compare sets by label.",
        "numeric_oracle": None,
        "warmup_excluded": 0,
        "concurrency": 1,
        "mutation_retries": 0,
        "timeout_seconds_per_mcp_call": 180,
        "stop_on_technical_failure": True,
        "independent_readback": (
            "Fresh MCP session after restoring original CCaaS, all completed trials."
        ),
        "latency_scope": (
            "Monotonic MCP wall time includes REST, native ontology/reasoning "
            "and Fabric transaction; "
            "not pure C++ time."
        ),
        "e2e_scope": (
            "Sum of five measured calls; excludes stdio startup/discovery, "
            "local archive writes and later readback."
        ),
        "statistics": (
            "n/min/median/max, sample stdev; descriptive, "
            "no throughput or asymptotic scaling claim."
        ),
        "ontology_path": BASELINE,
        "image_id": IMAGE,
        "weight_sensitivity": (
            "Not evaluated: existing input/API exposes ID/type and endpoints, "
            "no numeric weight sweep."
        ),
        "against_label_policy": (
            "Verify directed paths/products separately from sign interpretation; "
            "report disagreements."
        ),
        "reuse": [
            "Existing Go client store/rank/read sequence and tolerances; "
            "MCP stdio smoke collector.",
            "Five versioned fixture pairs, scientific expected-clash catalog.",
            "Reversible CCaaS deployment procedure from "
            "output/case-improvements-20261106/deploy_argumentation.py.",
        ],
        "caliper": (
            "Existing mixed user-registry workload targets a different contract; "
            "not used for ranking latency."
        ),
        "no_product_or_semantic_extension": True,
    }
    write(out / "protocol.json", protocol)
    print(
        json.dumps({"prepared": str(out), "trials": 30, "protected_files": len(protected)}),
        flush=True,
    )


def check_frozen(out):
    protocol = read(out / "protocol.json")
    if (
        sha(Path(__file__)) != protocol["collector_sha256"]
        or sha(out / "scientific-cases.json") != protocol["scientific_cases_sha256"]
    ):
        raise ValueError("Collector/catalog changed after protocol freeze")
    for name, digest in protocol["input_sha256"].items():
        if sha(out / "inputs" / name) != digest:
            raise ValueError("Frozen input changed")
    return protocol


@contextmanager
def baseline_runtime(out):
    before = runtime()
    write(out / "runtime-before.json", before)
    if before["image"] != IMAGE or not before["state"]["Running"]:
        raise ValueError("Unexpected native runtime image/state")
    catalog = read(out / "scientific-cases.json")
    if (
        catalog["baseline_ontology_sha256"] not in before["sha256"]
        or catalog["native_library_sha256"] not in before["sha256"]
    ):
        raise ValueError("Unexpected baseline ontology/native library")
    info = json.loads(run("docker", "inspect", CONTAINER))[0]
    network = list(info["NetworkSettings"]["Networks"])
    if len(network) != 1:
        raise ValueError("Expected one existing Fabric network")
    suffix = out.name.replace("-", "_")
    backup = CONTAINER + "_preserved_" + suffix
    retained = CONTAINER + "_stopped_" + suffix
    # Same immutable image, environment and bind mounts; only ontology selection differs.
    args = [
        "docker",
        "create",
        "--platform",
        "linux/amd64",
        "--name",
        CONTAINER,
        "--network",
        network[0],
    ]
    for item in info["Config"]["Env"]:
        if not item.startswith("ARGUMENTATION_ONTOLOGY_PATH="):
            args.extend(["-e", item])
    args.extend(["-e", "ARGUMENTATION_ONTOLOGY_PATH=" + BASELINE])
    for mount in info["Mounts"]:
        if mount["Type"] != "bind":
            raise ValueError("Unexpected mount type")
        args.extend(
            ["-v", mount["Source"] + ":" + mount["Destination"] + ("" if mount["RW"] else ":ro")]
        )
    for port, bindings in (info["HostConfig"].get("PortBindings") or {}).items():
        for binding in bindings:
            host = binding["HostIp"]
            args.extend(["-p", (host + ":" if host else "") + binding["HostPort"] + ":" + port])
    args.append(IMAGE)
    run("docker", "stop", CONTAINER)
    run("docker", "rename", CONTAINER, backup)
    try:
        created = run(*args)
        write(
            out / "runtime-switch.json",
            {
                "created_utc": utc(),
                "benchmark_container_id": created,
                "original_container_id": before["id"],
                "preserved_original": backup,
                "retained_benchmark_container": retained,
                "image": IMAGE,
                "network": network[0],
                "ontology": BASELINE,
            },
        )
        run("docker", "start", CONTAINER)
        write(out / "runtime-during.json", runtime())
        yield
    finally:
        current = subprocess.run(["docker", "inspect", CONTAINER], capture_output=True, text=True)
        if current.returncode == 0:
            subprocess.run(["docker", "stop", CONTAINER], check=True, capture_output=True)
            run("docker", "rename", CONTAINER, retained)
        run("docker", "rename", backup, CONTAINER)
        run("docker", "start", CONTAINER)
        after = runtime()
        write(out / "runtime-restored.json", after)
        if (
            after["id"] != before["id"]
            or after["ontology_env"] != before["ontology_env"]
            or after["sha256"] != before["sha256"]
        ):
            raise ValueError("Original native container not restored exactly")


async def session_calls(out, protocol, independent=False):
    from dotenv import dotenv_values
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client

    environment = os.environ.copy()
    environment.update({k: v for k, v in dotenv_values(BRIDGE / ".env").items() if v is not None})
    environment.update(
        FABLO_REST_URL="http://127.0.0.1:8800",
        FABLO_INVOKE_PATH="/invoke/{channel}/{chaincode}",
        FABLO_QUERY_PATH="/query/{channel}/{chaincode}",
    )
    params = StdioServerParameters(
        command=str(NODE), args=[str(BRIDGE / "build/index.js")], cwd=str(BRIDGE), env=environment
    )
    phase = "readback" if independent else "collection"
    events = []
    with (out / f"{phase}.stderr.log").open("x") as stderr:
        async with stdio_client(params, errlog=stderr) as (r, w):
            async with ClientSession(r, w, read_timeout_seconds=timedelta(seconds=180)) as session:
                await session.initialize()
                write(
                    out / f"{phase}-discovery.json",
                    (await session.list_tools()).model_dump(mode="json"),
                )
                for trial in protocol["trials"]:
                    directory = out / "trials" / trial["id"]
                    if independent and not (directory / "completed.json").exists():
                        continue
                    graph = read(out / "inputs" / f"{trial['case']}-{trial['variant']}.json")
                    names = (
                        protocol["calls_per_trial"][2:]
                        if independent
                        else protocol["calls_per_trial"]
                    )
                    for name in names:
                        arguments = {"graph_id": trial["graph_id"]}
                        if name == "store_graph":
                            arguments["graph"] = graph
                        observed = utc()
                        start = time.perf_counter()
                        event = {
                            "trial": trial["id"],
                            "graph_id": trial["graph_id"],
                            "tool": name,
                            "observed_utc": observed,
                        }
                        try:
                            reply = await session.call_tool(name, arguments)
                            event["elapsed_seconds"] = time.perf_counter() - start
                            raw = reply.model_dump(mode="json")
                            write(directory / f"{phase}-{name}.json", raw)
                            result = unwrap(raw)
                            if name in ["store_graph", "rank_graph"] and result != "OK":
                                raise ValueError("Mutation did not acknowledge OK")
                            if independent:
                                original = unwrap(read(directory / f"collection-{name}.json"))
                                if result != original:
                                    raise ValueError("Independent readback differs")
                            if name == "get_graph" and result != graph:
                                raise ValueError("Stored graph differs from input")
                            event["success"] = True
                        except Exception as exc:
                            event.setdefault("elapsed_seconds", time.perf_counter() - start)
                            event.update(
                                success=False, error_type=type(exc).__name__, error=str(exc)[:1000]
                            )
                            events.append(event)
                            with (out / f"{phase}-events.jsonl").open("a") as stream:
                                stream.write(json.dumps(event) + "\n")
                            raise
                        events.append(event)
                        with (out / f"{phase}-events.jsonl").open("a") as stream:
                            stream.write(json.dumps(event) + "\n")
                    write(directory / f"{phase}-timings.json", events[-len(names) :])
                    if not independent:
                        write(directory / "completed.json", {"completed_utc": utc(), **trial})
                    print(json.dumps({"phase": phase, "completed": trial["id"]}), flush=True)


def collect(out):
    protocol = check_frozen(out)
    write(
        out / "collection-started.json",
        {"observed_utc": utc(), "protocol_sha256": sha(out / "protocol.json")},
    )
    failure = None
    try:
        with baseline_runtime(out):
            asyncio.run(session_calls(out, protocol))
    except Exception as exc:
        failure = {"error_type": type(exc).__name__, "error": str(exc)[:1200]}
    # Reads only: neither ranking nor ontology loading is needed after restoration.
    try:
        asyncio.run(session_calls(out, protocol, independent=True))
    except Exception as exc:
        failure = {
            "previous": failure,
            "readback_error_type": type(exc).__name__,
            "error": str(exc)[:1200],
        }
    protected = read(out / "protected-before.json")
    changed = [
        name
        for name, digest in protected.items()
        if not Path(name).is_file() or sha(Path(name)) != digest
    ]
    repos = {
        name: {
            "branch": run("git", "-C", name, "branch", "--show-current"),
            "head": run("git", "-C", name, "rev-parse", "HEAD"),
        }
        for name in protocol["repositories"]
    }
    write(
        out / "collection-closure.json",
        {
            "observed_utc": utc(),
            "failure": failure,
            "protected_files": len(protected),
            "changed_protected_files": changed,
            "repositories_unchanged": repos == protocol["repositories"],
            "completed_trials": sum(
                (out / "trials" / t["id"] / "completed.json").exists() for t in protocol["trials"]
            ),
            "independent_readback_trials": sum(
                (out / "trials" / t["id"] / "readback-timings.json").exists()
                for t in protocol["trials"]
            ),
        },
    )
    if changed or repos != protocol["repositories"] or failure:
        raise RuntimeError("Collection has recorded failures; inspect collection-closure.json")


def describe(values):
    return {
        "n": len(values),
        "min_seconds": min(values),
        "median_seconds": statistics.median(values),
        "max_seconds": max(values),
        "sample_stdev_seconds": statistics.stdev(values) if len(values) > 1 else None,
    }


def analyze(out):
    protocol = check_frozen(out)
    catalog = {c["id"]: c for c in read(out / "scientific-cases.json")["cases"]}
    results = []
    for trial in protocol["trials"]:
        directory = out / "trials" / trial["id"]
        row = {**trial, "completed": (directory / "completed.json").exists()}
        if row["completed"]:
            graph = read(out / "inputs" / f"{trial['case']}-{trial['variant']}.json")
            native = unwrap(read(directory / "collection-get_annotated_graph.json"))
            rank = unwrap(read(directory / "collection-get_rank_result.json"))
            row["audit"] = audit(graph, rank, native, catalog[trial["case"]])
            row["seconds"] = {
                e["tool"]: e["elapsed_seconds"] for e in read(directory / "collection-timings.json")
            }
            row["seconds"]["five_call_sum"] = sum(row["seconds"].values())
            row["independent_readback_equal"] = (directory / "readback-timings.json").exists()
        results.append(row)
    comparisons = []
    for case in catalog:
        selected = [r for r in results if r["case"] == case]
        # All three pairwise comparisons within each variant; three paired permutations.
        for a, b in itertools.combinations(selected, 2):
            if a["variant"] == b["variant"] or a["repetition"] == b["repetition"]:
                kind = "repeat" if a["variant"] == b["variant"] else "permutation"
                value = (
                    compare(a["audit"]["scores"], b["audit"]["scores"])
                    if a["completed"] and b["completed"]
                    else {"comparable": False, "scores_equal": False, "winner_equal": False}
                )
                weights_equal = (
                    (a["audit"]["weights_by_label"] == b["audit"]["weights_by_label"])
                    if value["comparable"]
                    else None
                )
                comparisons.append(
                    {
                        "case": case,
                        "kind": kind,
                        "a": a["id"],
                        "b": b["id"],
                        **value,
                        "relation_weights_exact": weights_equal,
                    }
                )
    cases = []
    for case, fixture in catalog.items():
        rows = [r for r in results if r["case"] == case and r["completed"]]
        cs = [c for c in comparisons if c["case"] == case]
        cases.append(
            {
                "case": case,
                "nodes": fixture["nodes"],
                "edges": fixture["edges"],
                "completed": len(rows),
                "candidate_count": len(rows[0]["audit"]["scores"]) if rows else None,
                "winner_sets": sorted({tuple(r["audit"]["winners_within_1e_6"]) for r in rows}),
                "comparisons": dict(Counter(c["kind"] for c in cs)),
                "score_comparisons_passed": sum(c["scores_equal"] for c in cs),
                "winner_comparisons_passed": sum(c["winner_equal"] for c in cs),
                "max_absolute_score_delta": max(
                    (c["max_absolute_delta"] for c in cs if c["comparable"]), default=None
                ),
                "latencies": {
                    tool: describe([r["seconds"][tool] for r in rows])
                    for tool in [*protocol["calls_per_trial"], "five_call_sum"]
                }
                if rows
                else {},
            }
        )
    summary = {
        "protocol_sha256": sha(out / "protocol.json"),
        "planned": len(results),
        "completed": sum(r["completed"] for r in results),
        "cases": cases,
        "repeat_comparisons": sum(c["kind"] == "repeat" for c in comparisons),
        "permutation_comparisons": sum(c["kind"] == "permutation" for c in comparisons),
        "all_scores_within_tolerance": all(c["scores_equal"] for c in comparisons),
        "all_winner_sets_equal": all(c["winner_equal"] for c in comparisons),
        "independent_readback_equal": sum(
            r.get("independent_readback_equal", False) for r in results
        ),
        "paths_checked": sum(len(r.get("audit", {}).get("paths", [])) for r in results),
        "invalid_path_products": sum(
            not p["directed_path_and_product_valid"]
            for r in results
            for p in r.get("audit", {}).get("paths", [])
        ),
        "sign_interpretation_disagreements": sum(
            r.get("audit", {}).get("sign_interpretation_disagreements", 0) for r in results
        ),
        "candidates_without_paths": sum(
            len(r.get("audit", {}).get("candidates_without_paths", [])) for r in results
        ),
        "numeric_oracle": None,
        "weight_sensitivity": "not_evaluated",
        "offchain_onchain_overhead": "not_measured",
        "pure_native_compute_latency": "not_isolated",
    }
    write(out / "trial-analysis.json", results)
    write(out / "comparisons.json", comparisons)
    write(out / "metrics.json", summary)
    with (out / "latencies.csv").open("x", newline="") as stream:
        fields = [
            "trial",
            "case",
            "variant",
            "repetition",
            "completed",
            *protocol["calls_per_trial"],
            "five_call_sum",
        ]
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for r in results:
            writer.writerow(
                {"trial": r["id"], **{k: r[k] for k in fields[1:5]}, **r.get("seconds", {})}
            )
    print(json.dumps(summary, indent=2), flush=True)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=["prepare", "collect", "analyze"])
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    {"prepare": prepare, "collect": collect, "analyze": analyze}[args.command](
        args.output.resolve()
    )
