"""Inventory archived evidence without importing agents or contacting any service.

Run with Python's standard library. Inputs are read-only; outputs must go into
a new directory. Timings come only from explicit recorded durations, never file
names, mtimes, conversation timestamps, or subtraction of unrelated runs.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import os
import re
import subprocess
from collections import Counter
from datetime import datetime
from pathlib import Path

WORKSPACE = Path(__file__).resolve().parents[1]
TRACE_FILES = (
    "shared_mcp_events.jsonl",
    "sources/mcp_events.jsonl",
    "sources/telemetry_events.jsonl",
    "sources/supply_chain_events.jsonl",
    "preparation/preparation_events.jsonl",
    "strategic/strategic_events.jsonl",
    "validation/validation_events.jsonl",
)
BOUNDARIES = {
    "collect_telemetry": "Gateway HTTP su export gia raccolto; esclude raccolta SDK originale.",
    "collect_supply_chain": "Gateway SBOM/OSV; include trasporto ed elaborazione del servizio.",
    "assess_software": "Chiamata CTI MCP; esclude il resto dell'agente LLM.",
    "prepare_argumentation": "Preparazione aggregata: verifiche fonti, OWL, grafo e ALN.",
    "rank_remediations": "Dominio SaaS aggregato; include storage/ranking, non solo core BWAF.",
    "get_decision": "Rilettura della decisione SaaS tramite MCP.",
    "get_provenance": "Rilettura della provenance della decisione tramite MCP.",
    "validate_countermeasure": "Dominio semantico/operativo via MCP; non tempo puro CGO.",
    "finalize_recommendation": "Validazioni, registrazione, commit e verifiche del backend.",
    "get_finalization": "Rilettura/verifica della finalizzazione tramite MCP.",
}
STATUS_LABELS = {
    "disponibile_circoscritta": "Disponibile, perimetro limitato",
    "parziale": "Parziale",
    "solo_test_o_mock": "Solo test/mock per il criterio",
    "mancante": "Mancante",
    "non_eseguita": "Non eseguita nel percorso",
}


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def duration(value):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    return float(value) if math.isfinite(value) and value >= 0 else None


def optional(path):
    return load(path) if path.exists() else {}


def git_state(root):
    if not root.exists():
        return {"available": False}
    env = {**os.environ, "GIT_OPTIONAL_LOCKS": "0"}

    def git(*args):
        return subprocess.check_output(["git", "-C", str(root), *args], text=True, env=env).strip()

    return {
        "available": True,
        "branch": git("branch", "--show-current"),
        "head_at_inventory": git("rev-parse", "HEAD"),
        "dirty_at_inventory": bool(git("status", "--porcelain")),
        "scope": "Stato locale alla raccolta; non attribuito retroattivamente ai run.",
    }


def inventory(config, roots):
    records = {}
    unmatched = []
    for group in config["groups"]:
        root = roots[group["repository"]]
        for pattern in group["patterns"]:
            found = False
            for path in sorted(root.glob(pattern)):
                if not path.is_file() or path.is_symlink():
                    continue
                if any(part in {".git", "node_modules", "__pycache__"} for part in path.parts):
                    continue
                if path.name.startswith(".env"):
                    continue
                found = True
                relative = path.relative_to(root).as_posix()
                key = group["repository"] + ":" + relative
                if key not in records:
                    records[key] = {
                        "id": key,
                        "repository": group["repository"],
                        "path": relative,
                        "size_bytes": path.stat().st_size,
                        "sha256": sha(path),
                        "groups": [],
                    }
                records[key]["groups"].append(group["id"])
            if not found:
                unmatched.append({"group": group["id"], "pattern": pattern})
    return sorted(records.values(), key=lambda row: row["id"]), unmatched


def launcher_row(summary_path, run_dir, batch, kind):
    summary = load(summary_path)
    execution = optional(run_dir / "execution.json") or summary.get("execution", {})
    recommendation = optional(run_dir / "recommendation/native_strategic_recommendation.json")
    validation = optional(run_dir / "validation/native_strategic_validation.json")
    finalization = optional(run_dir / "finalization/native_strategic_finalization.json")
    dag = optional(run_dir / "dag.json")
    outcomes = execution.get("outcomes_by_cve", {})
    if execution.get("outcome"):
        outcomes = {"assessment": execution["outcome"]}
    if not outcomes and summary.get("outcome"):
        outcomes = {"assessment": summary["outcome"]}
    if recommendation.get("results"):
        outcomes = {r["cve_id"]: r["outcome"] for r in recommendation["results"]}
    selected = [
        r["selected_strategy_id"]
        for r in recommendation.get("results", [])
        if r.get("selected_strategy_id") is not None
    ]
    results = finalization.get("results", [])
    final = results[0] if len(results) == 1 else {}
    native = [a["response"]["reasoning"]["native"] for a in validation.get("attempts", [])]
    nodes = list(dag.get("nodes", {}).values())
    status = execution.get("status", summary.get("status"))
    full = kind == "full_launcher"
    return {
        "key": batch + ":" + run_dir.name,
        "batch": batch,
        "case": summary.get("case", run_dir.name.split("-")[0]),
        "attempt": summary.get("attempt"),
        "kind": kind,
        "summary": summary_path.relative_to(WORKSPACE).as_posix(),
        "run_directory": run_dir.relative_to(WORKSPACE).as_posix(),
        "run_id": execution.get("run_id"),
        "status": status,
        "exit_code": summary.get("exit_code"),
        "error_type": execution.get("error_type"),
        "elapsed_seconds": duration(summary.get("elapsed_seconds")),
        "duration_boundary": "Runner, inclusa chiusura gateway" if full else kind,
        "launcher_completed": full and status in {"dry_run_completed", "assessment_completed"},
        "domain_outcomes": outcomes,
        "selected_strategy_ids": selected,
        "shared_finalization": execution.get("shared_finalization"),
        "dag_nodes_completed": sum(n.get("status") == "completed" for n in nodes),
        "dag_nodes_total": len(nodes) if nodes else None,
        "recorded_commit": final.get("commit"),
        "ledger_readback_verified": final.get("ledger_readback_verified"),
        "semantic_abduction_penalties": [n["abductionPenalty"] for n in native],
        "operational_statuses": [
            a["response"].get("operational", {}).get("status")
            for a in validation.get("attempts", [])
        ],
        "sampling": "Diagnostica; non serie congelata di repliche indipendenti.",
    }


def collect_runs(config):
    current = WORKSPACE / config["current_batch"]
    earlier = WORKSPACE / config["earlier_batch"]
    rows = []
    for path in sorted((current / "cases").glob("*/summary.json")):
        if re.fullmatch(r"C[1-4]-r\d+", path.parent.name):
            rows.append(
                launcher_row(
                    path, current / "runs" / path.parent.name, "logback_v2", "full_launcher"
                )
            )
    for path in sorted((current / "runs").glob("C4-r1-finalization-r*/summary.json")):
        rows.append(launcher_row(path, path.parent, "logback_v2", "finalization_continuation"))
    for path in sorted((earlier / "runs").glob("*/summary.json")):
        rows.append(launcher_row(path, path.parent, "log4j_v1", "earlier_source_attempt"))
    return rows


def collect_timings(runs):
    rows = []
    for run in runs:
        if run["batch"] != "logback_v2":
            continue
        for relative in TRACE_FILES:
            path = WORKSPACE / run["run_directory"] / relative
            if not path.exists():
                continue
            for line_number, line in enumerate(path.read_text().splitlines(), 1):
                if not line.strip():
                    continue
                event = json.loads(line)
                tool = event.get("tool") or event.get("event")
                if tool in {None, "connected"}:
                    continue
                elapsed = duration(event.get("elapsed_seconds"))
                if "elapsed_seconds" in event and elapsed is None:
                    raise ValueError(f"Invalid explicit timing: {path}:{line_number}")
                wall = None
                if event.get("started_at") and event.get("ended_at"):
                    start = datetime.fromisoformat(event["started_at"].replace("Z", "+00:00"))
                    end = datetime.fromisoformat(event["ended_at"].replace("Z", "+00:00"))
                    wall = (end - start).total_seconds()
                rows.append(
                    {
                        "run_key": run["key"],
                        "case": run["case"],
                        "kind": run["kind"],
                        "tool": tool,
                        "status": event.get("status"),
                        "elapsed_seconds": elapsed,
                        "duration_recorded": elapsed is not None,
                        "wall_clock_seconds": wall,
                        "wall_clock_agrees_50ms": (
                            abs(wall - elapsed) <= 0.05
                            if wall is not None and elapsed is not None
                            else None
                        ),
                        "boundary": BOUNDARIES.get(tool, "Evento senza timer isolato."),
                        "source": path.relative_to(WORKSPACE).as_posix(),
                        "source_line": line_number,
                        "call_id": event.get("call_id"),
                    }
                )
    return rows


def collect_decisions(runs):
    rows = []
    for run in runs:
        if run["batch"] != "logback_v2" or run["kind"] != "full_launcher":
            continue
        directory = WORKSPACE / run["run_directory"]
        ranking = optional(directory / "strategic/native_strategic_ranking.json")
        validation = optional(directory / "validation/native_strategic_validation.json")
        choice = optional(directory / "recommendation/native_strategic_recommendation.json")
        ranked = {r["cve_id"]: r for r in ranking.get("results", [])}
        choices = {r["cve_id"]: r for r in choice.get("results", [])}
        for attempt in validation.get("attempts", []):
            response = attempt["response"]
            native = response["reasoning"]["native"]
            operational = response["operational"]
            native_rows = ranked[attempt["cve_id"]]["ranking"]["rankedStrategies"]
            strategy = next(r for r in native_rows if r["id"] == attempt["ontology_individual"])
            method = strategy.get("explanation", {}).get("method")
            decision = choices.get(attempt["cve_id"], {})
            rows.append(
                {
                    "run_key": run["key"],
                    "launcher_completed": run["launcher_completed"],
                    "cve_id": attempt["cve_id"],
                    "strategy_id": attempt["strategy_id"],
                    "ontology_individual": attempt["ontology_individual"],
                    "rank": strategy["rank"],
                    "ranking_score": strategy["score"],
                    "ranking_method": method,
                    "native_bwaf_computed": False
                    if method == "single_candidate_convention_v1"
                    else None,
                    "semantic_status": response["status"],
                    "semantic_valid": response["valid"],
                    "abduction_penalty": native["abductionPenalty"],
                    "contraction_penalty": native["contractionPenalty"],
                    "abduction_executed": bool(native["hypothesis"].strip()),
                    "contraction_executed": bool(native["giveUp"].strip()),
                    "bonus_evaluated": response["bonusEvaluated"],
                    "native_affinity_score": native["score"],
                    "operational_status": operational["status"],
                    "missing_capabilities": operational["missing_capabilities"],
                    "unassessed_constraints": operational["unassessed_constraints"],
                    "effective_status": response["effectiveStatus"],
                    "outcome": decision.get("outcome"),
                    "selected_strategy_id": decision.get("selected_strategy_id"),
                    "source": run["run_directory"] + "/validation/native_strategic_validation.json",
                }
            )
    return rows


def integrity_checks(config, roots, records):
    checks = []

    def check(name, passed, source, detail):
        checks.append({"check": name, "passed": bool(passed), "source": source, "detail": detail})

    proposal = WORKSPACE / config["proposal"]
    check(
        "proposal_sha256",
        sha(proposal) == config["proposal_sha256"],
        config["proposal"],
        "Digest della proposta coincidente con il registro fonti.",
    )
    base = WORKSPACE / config["current_batch"]
    for variant in ("vulnerable", "negative"):
        source = base / "sources" / variant
        manifest = load(source / "source_manifest.json")
        for name, expected in manifest["files"].items():
            path = source / name
            check(
                f"source_{variant}_{name}",
                path.exists() and sha(path) == expected,
                path.relative_to(WORKSPACE).as_posix(),
                "Confronto con manifest originale.",
            )
    backup = load(base / "saas-data-C1-manifest.json")
    for relative, expected in backup["files_sha256"].items():
        path = base / "saas-data-C1" / relative
        check(
            "C1_backup_" + relative,
            path.exists() and sha(path) == expected,
            path.relative_to(WORKSPACE).as_posix(),
            "Backup autentico, nessuna ricostruzione.",
        )
    run = base / "runs/C1-r2"
    final = load(run / "finalization/native_strategic_finalization.json")["results"][0]
    record = final["record"]
    for field in ("document", "provenance"):
        actual = "sha256:" + hashlib.sha256(record[field + "_json"].encode()).hexdigest()
        check(
            "C1_" + field + "_digest",
            actual == record[field + "_sha256"],
            (run / "finalization/native_strategic_finalization.json")
            .relative_to(WORKSPACE)
            .as_posix(),
            "Hash delle stringhe originali UTF-8, senza riserializzarle.",
        )
    commit = final["commit"]
    check(
        "C1_commit_receipt",
        commit["successful"] is True
        and commit["validation_code"] == 0
        and commit["transaction_id"] == record["transaction_id"],
        (run / "finalization/native_strategic_finalization.json").relative_to(WORKSPACE).as_posix(),
        "Coerenza della ricevuta archiviata, senza contattare Fabric.",
    )
    for filename in ("aln_ontology.owl", "observed_assets.owl"):
        check(
            "C1_preparation_" + filename,
            (run / "preparation" / filename).read_bytes()
            == (base / "semantics" / filename).read_bytes(),
            (run / "preparation" / filename).relative_to(WORKSPACE).as_posix(),
            "Preparazione C1 identica agli input della distribuzione archiviata.",
        )
    deployment = load(base / "semantics/deployment-r2/deployment.json")
    check(
        "deployed_ontology_hash",
        sha(base / "semantics/deployed_ontology.owl") == deployment["ontology_sha256"],
        config["current_batch"] + "/semantics/deployed_ontology.owl",
        "Digest confrontato con il deployment, non nuova verifica del container.",
    )
    native = load(run / "validation/native_strategic_validation.json")["attempts"][0]
    check(
        "C1_native_result_matches_deployment",
        native["response"]["reasoning"]["native"] == deployment["explanation"],
        config["current_batch"] + "/runs/C1-r2/validation/native_strategic_validation.json",
        "Stesso risultato nativo e stessi binding archiviati.",
    )
    reread = load(base / "C1-postrun-readback.json")
    check(
        "C1_archived_readback_receipt",
        reread["record_and_provenance_exactly_equal"] is True
        and reread["original_transaction_id"] == commit["transaction_id"],
        config["current_batch"] + "/C1-postrun-readback.json",
        "Coerenza della prova di rilettura gia raccolta; non una nuova query.",
    )
    verification = load(base / "verification-C1.json")
    for key, repository in (
        ("framework_source_sha256", "framework"),
        ("pipeline_source_sha256", "pipeline"),
        ("external_source_sha256", "ledger"),
    ):
        for relative, expected in verification.get(key, {}).items():
            path = roots[repository] / relative
            check(
                "archived_source_" + repository + ":" + relative,
                path.exists() and sha(path) == expected,
                repository + ":" + relative,
                "Confronto con hash al collaudo; una differenza segnala deriva del codice.",
            )
    check(
        "unique_inventory_paths",
        len({r["id"] for r in records}) == len(records),
        "inventory.json",
        "Un file puo appartenere a piu gruppi ma viene inventariato una volta.",
    )
    return checks


def write_json(path, data):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False, allow_nan=False) + "\n")


def write_csv(path, rows, fields):
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    key: json.dumps(value, ensure_ascii=False)
                    if isinstance(value, (dict, list))
                    else ""
                    if value is None
                    else value
                    for key in fields
                    for value in [row.get(key)]
                }
            )


def report(config, output, roots, records, groups, metrics, runs, timings, checks):
    def link(path, label):
        return f"[{label}]({Path(os.path.relpath(path, output)).as_posix()})"

    def evidence_links(ids):
        return ", ".join(f"[{name}](#evidenze-{name.replace('_', '-')})" for name in ids)

    def cell(value):
        return str(value).replace("|", "\\|").replace("\n", " ")

    def seconds(value):
        return "n.d." if value is None else f"{value:.6f}"

    lines = [
        f"# Inventario evidenze e copertura metriche — {config['as_of']}",
        "",
        "Raccolta offline degli archivi locali. Nessun nuovo run, test backend, enrollment, "
        "query o scrittura Fabric. Il limite semantico C1 resta nel perimetro concordato.",
        "",
        "Fonte dei requisiti: "
        + link(WORKSPACE / config["proposal"], "proposta iniziale")
        + ", sezioni 15.1–15.5. Hash del PDF verificato contro il registro fonti.",
        "",
        f"Inventariati **{len(records)} file univoci**, in {len(groups)} gruppi. "
        "Il perimetro e dichiarato nel catalogo; non e una scansione completa del filesystem. "
        "Hash e percorsi non sostituiscono una valutazione indipendente di accuratezza.",
        "",
        "## File della raccolta",
        "",
        "- [Inventario JSON](inventory.json) e [CSV](inventory.csv): "
        "percorso, dimensione, SHA-256 e gruppi.",
        "- [Copertura JSON](coverage.json) e [CSV](coverage.csv): "
        "requisito, stato, evidenze e lacuna.",
        "- [Tentativi JSON](runs.json) e [CSV](runs.csv): "
        "launcher, riprese e diagnostica precedente separati.",
        "- [Latenze JSON](latencies.json) e [CSV](latencies.csv): "
        "osservazioni con file/riga e confine temporale.",
        "- [Decisioni JSON](decisions.json) e [CSV](decisions.csv): "
        "ranking, penalita native, vincoli ed esito prima/dopo validazione.",
        "- [Verifiche di integrita](checks.json) e [manifest della raccolta](manifest.json).",
        "",
        "## Criteri di lettura",
        "",
        "- `Disponibile, perimetro limitato`: osservazione reale archiviata, "
        "senza generalizzazione statistica.",
        "- `Parziale`: evidenza utile, ma confronto, isolamento temporale "
        "o serie sperimentale incompleti.",
        "- `Solo test/mock`: il criterio non e dimostrato dal percorso integrato reale.",
        "- `Mancante` / `Non eseguita`: valore non misurato, "
        "da lasciare nullo, mai sostituito con zero.",
        "- Nessuna percentuale globale di conformita: "
        "le metriche hanno significati e denominatori diversi.",
        "- Nessuna media fra batch, casi, revisioni, continuazioni o tempi falliti/riusciti.",
        "",
        "## Tentativi della campagna Logback",
        "",
        "Le durate sono quelle esplicite del runner, con teardown dei gateway incluso. "
        "Le fonti SDK sono gia raccolte: non e latenza dall'evento runtime alla decisione.",
        "",
        "| Tentativo | Tipo | Stato tecnico | Secondi runner | "
        "Esito decisionale | DAG completati |",
        "| --- | --- | --- | ---: | --- | --- |",
    ]
    for row in runs:
        if row["batch"] != "logback_v2":
            continue
        dag = (
            f"{row['dag_nodes_completed']}/{row['dag_nodes_total']}"
            if row["dag_nodes_total"] is not None
            else "n.d."
        )
        outcomes = ", ".join(sorted(set(row["domain_outcomes"].values()))) or "n.d."
        lines.append(
            "| "
            + " | ".join(
                [
                    link(WORKSPACE / row["summary"], row["key"].split(":", 1)[1]),
                    row["kind"],
                    row["status"] or "n.d.",
                    seconds(row["elapsed_seconds"]),
                    outcomes,
                    dag,
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "C1-r2: launcher completato, commit nel blocco 22, rilettura archiviata coerente; "
            "`requires_prerequisites`, nessuna candidata selezionata. C2/C3: assessment completo, "
            "fasi native non applicabili. C4-r1: launcher fallito sulla rilettura, "
            "pur avendo un record preservato nel ledger. Le riprese non trasformano "
            "il tentativo originale in un successo.",
            "",
            "Il protocollo v2 dichiara l'esito semantico gia osservato: "
            "serve a riprodurre il limite, "
            "non e un oracle indipendente di applicabilita. C1/C4 hanno una sola candidata e score "
            "`single_candidate_convention_v1`, non una misura del ranking BWAF.",
            "",
            "## Latenze direttamente recuperate: C1-r2",
            "",
            "| Operazione | Secondi | Confine della misura | Evidenza |",
            "| --- | ---: | --- | --- |",
        ]
    )
    for row in timings:
        if row["run_key"] == "logback_v2:C1-r2" and row["duration_recorded"]:
            label = Path(row["source"]).name + ":" + str(row["source_line"])
            lines.append(
                "| "
                + " | ".join(
                    [
                        row["tool"],
                        seconds(row["elapsed_seconds"]),
                        row["boundary"],
                        link(WORKSPACE / row["source"], label),
                    ]
                )
                + " |"
            )
    lines.extend(
        [
            "",
            "I timer OWL/grafo/ALN sono un'unica preparazione aggregata. "
            "`rank_remediations` e `finalize_recommendation` sono chiamate di dominio aggregate. "
            "Non sono i tempi puri del core, di StoreGraph o della sola scrittura PROV-O. "
            "La somma delle chiamate non ricostruisce il tempo degli agenti LLM; l'eventuale "
            "tempo residuo non viene attribuito automaticamente all'inferenza.",
            "",
            "## Copertura dei requisiti",
            "",
        ]
    )
    for section in ("15.1", "15.2", "15.3", "15.4", "15.5"):
        lines.extend(
            [
                f"### Proposta, sezione {section}",
                "",
                "| ID | Metrica | Stato | Evidenze disponibili | Lacuna / verifica residua |",
                "| --- | --- | --- | --- | --- |",
            ]
        )
        for row in metrics:
            if row["section"] == section:
                lines.append(
                    "| "
                    + " | ".join(
                        [
                            row["id"],
                            row["name"],
                            STATUS_LABELS[row["status"]],
                            cell(row["available"]) + " " + evidence_links(row["evidence"]),
                            cell(row["gap"]),
                        ]
                    )
                    + " |"
                )
        lines.append("")
    lines.extend(
        [
            "## Inventario per gruppo",
            "",
            "Ogni file e identificato nell'inventario JSON/CSV; qui sono mostrati "
            "conteggi e riferimenti principali. Le copie di lineage sono conservate "
            "nell'inventario ma escluse dalla raccolta dei timer primari.",
            "",
        ]
    )
    for group in groups:
        lines.extend(
            [
                f"### Evidenze {group['id'].replace('_', '-')}",
                "",
                group["description"],
                "",
                f"Repository `{group['repository']}`; tipo `{group['kind']}`; "
                f"**{group['file_count']} file**, {group['size_bytes']} byte.",
                "",
            ]
        )
        candidates = [r for r in records if group["id"] in r["groups"]]
        preferred = sorted(
            candidates,
            key=lambda r: (
                0
                if Path(r["path"]).name
                in {
                    "report-C1.md",
                    "verification-C1.json",
                    "baseline-graphs.json",
                    "summary.json",
                    "results.json",
                    "native-benchmark-audit.json",
                    "proposta-agentic-cti.pdf",
                    "source_manifest.json",
                }
                else 1,
                len(Path(r["path"]).parts),
                r["path"],
            ),
        )[:5]
        lines.extend("- " + link(roots[r["repository"]] / r["path"], r["path"]) for r in preferred)
        lines.append("")
    failed = [c for c in checks if not c["passed"]]
    lines.extend(
        [
            "## Verifiche e limiti della raccolta",
            "",
            f"**{len(checks) - len(failed)}/{len(checks)} controlli di integrita coerenti** "
            "con gli archivi. Confronti su fonti, backup, stringhe finalizzate, "
            "ricevute e sorgenti "
            "hashati al collaudo; nessuna nuova verifica dello stato dei container o del ledger.",
            "",
            "- Mancano corpus manuale indipendente e conteggi TP/FP/FN: "
            "precisione/recall/F1 restano nulli.",
            "- Manca una serie omogenea di repliche: niente stime di stabilita o percentili.",
            "- Manca una campagna numerica sulle cinque coppie di grafi; "
            "l'analisi offline non la sostituisce.",
            "- Mancano una coppia con/senza runtime e un confronto on-chain/off-chain equivalente.",
            "- Bonus non invocato; contrazione non esercitata da C1; "
            "accettazione reale non dimostrata.",
            "- Il record C4 e conservato, ma i vecchi metadati SaaS non sono ricostruiti. "
            "Non eseguire suite SaaS nella directory del servizio attivo.",
            "",
            "## Prossimi passi minimi, non eseguiti",
            "",
            "1. Annotare un campione indipendente e definire regole/denominatori "
            "per estrazione e matching.",
            "2. Definire ambiente e ripetizioni prima di raccogliere nuovi run; completare C4.",
            "3. Riutilizzare il client e i cinque grafi esistenti per determinismo e dimensione.",
            "4. Valutare le ablation supportate dal percorso corrente "
            "e dichiarare quelle non realizzabili.",
            "5. Aggiornare la relazione con misure, numero di campioni e limiti; "
            "nessuna modifica ai Word manuali.",
            "",
        ]
    )
    if failed:
        lines.extend(["### Differenze da esaminare", ""])
        lines.extend(f"- `{row['check']}`: {row['detail']}" for row in failed)
        lines.append("")
    (output / "report.md").write_text("\n".join(lines), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--catalog", type=Path, default=WORKSPACE / "config/metrics-evidence.v1.json"
    )
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--pipeline",
        type=Path,
        default=Path.home() / "Desktop/agent-based-cti-argumentation-pipeline",
    )
    parser.add_argument(
        "--ledger", type=Path, default=Path.home() / "Desktop/semantic-cti-ledger-argumentation"
    )
    args = parser.parse_args()
    output = args.output.resolve()
    if output.exists():
        parser.error("Use a new output directory; previous evidence is never overwritten.")
    config = load(args.catalog)
    roots = {
        "framework": WORKSPACE,
        "pipeline": args.pipeline.resolve(),
        "ledger": args.ledger.resolve(),
    }
    records, unmatched = inventory(config, roots)
    runs = collect_runs(config)
    timings = collect_timings(runs)
    decisions = collect_decisions(runs)
    checks = integrity_checks(config, roots, records)
    metrics = config["metrics"]
    group_ids = {g["id"] for g in config["groups"]}
    assert len({m["id"] for m in metrics}) == len(metrics)
    assert all(set(m["evidence"]) <= group_ids for m in metrics)
    assert all(m["status"] in STATUS_LABELS for m in metrics)
    groups = []
    for group in config["groups"]:
        files = [r for r in records if group["id"] in r["groups"]]
        groups.append(
            {**group, "file_count": len(files), "size_bytes": sum(r["size_bytes"] for r in files)}
        )
    # Read all source files and validate before creating any output.
    repository_states = {name: git_state(path) for name, path in roots.items()}
    output.mkdir(parents=True)
    write_json(
        output / "inventory.json",
        {
            "contract": config["contract"],
            "as_of": config["as_of"],
            "groups": groups,
            "files": records,
            "unmatched_patterns": unmatched,
        },
    )
    write_csv(
        output / "inventory.csv",
        records,
        ["id", "repository", "path", "size_bytes", "sha256", "groups"],
    )
    write_json(
        output / "coverage.json",
        {
            "proposal": config["proposal"],
            "metrics": metrics,
            "status_counts": dict(Counter(m["status"] for m in metrics)),
        },
    )
    write_csv(
        output / "coverage.csv",
        metrics,
        ["id", "section", "name", "status", "evidence", "available", "gap", "next"],
    )
    write_json(output / "runs.json", runs)
    write_csv(output / "runs.csv", runs, list(runs[0]))
    write_json(output / "latencies.json", timings)
    write_csv(output / "latencies.csv", timings, list(timings[0]))
    write_json(output / "decisions.json", decisions)
    write_csv(output / "decisions.csv", decisions, list(decisions[0]))
    write_json(output / "checks.json", checks)
    report(config, output, roots, records, groups, metrics, runs, timings, checks)
    manifest = {
        "contract": config["contract"],
        "as_of": config["as_of"],
        "collection_scope": config["scope"],
        "catalog": args.catalog.resolve().relative_to(WORKSPACE).as_posix(),
        "catalog_sha256": sha(args.catalog),
        "collector_sha256": sha(Path(__file__)),
        "repositories": repository_states,
        "repository_roots": {k: str(v) for k, v in roots.items()},
        "inventory_files": len(records),
        "metrics": len(metrics),
        "current_full_launcher_attempts": sum(
            r["batch"] == "logback_v2" and r["kind"] == "full_launcher" for r in runs
        ),
        "current_completed_launchers": sum(r["launcher_completed"] for r in runs),
        "continuations": sum(r["kind"] == "finalization_continuation" for r in runs),
        "earlier_source_attempts": sum(r["kind"] == "earlier_source_attempt" for r in runs),
        "timing_observations": sum(t["duration_recorded"] for t in timings),
        "candidate_validation_observations": len(decisions),
        "events_without_isolated_timer": sum(not t["duration_recorded"] for t in timings),
        "failed_integrity_checks": [c["check"] for c in checks if not c["passed"]],
        "new_experiments_executed": False,
        "services_contacted": False,
        "missing_numeric_metrics": {
            key: None
            for key in (
                "precision",
                "recall",
                "f1",
                "product_matching_accuracy",
                "version_classification_accuracy",
                "blockchain_overhead",
            )
        },
        "outputs_sha256": {p.name: sha(p) for p in sorted(output.iterdir()) if p.is_file()},
    }
    write_json(output / "manifest.json", manifest)
    print(
        json.dumps(
            {
                k: manifest[k]
                for k in (
                    "inventory_files",
                    "metrics",
                    "current_full_launcher_attempts",
                    "current_completed_launchers",
                    "continuations",
                    "earlier_source_attempts",
                    "timing_observations",
                    "failed_integrity_checks",
                )
            },
            indent=2,
        )
    )
    return 1 if manifest["failed_integrity_checks"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
