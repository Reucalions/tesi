"""Build e osservazione dell'applicazione demo, esterni alla Workforce.

Genera una cartella nuova con SBOM della build, log SDK freschi, selettore e
profilo dei servizi. Non costruisce RuntimeEvidence, finding o candidate.
Il processo degli agenti continua a interrogare soltanto gli endpoint HTTP/MCP.
"""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
from datetime import UTC, datetime
from pathlib import Path

from thesis_agents.backends import BackendSettings
from thesis_agents.schemas.supply_chain import AssetBinding, SupplyChainQuery, select_component
from thesis_agents.schemas.telemetry_source import TelemetryInput, unix_nano

PROJECT = Path(__file__).resolve().parent
ROOT = PROJECT.parents[1]


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def inspect_sources(export, sbom, started_at, finished_at):
    """Verifica identità singola, freschezza e hash del JAR riportato dall'app."""
    observations = []
    for line in export.read_text(encoding="utf-8").splitlines():
        for resource_logs in json.loads(line)["resourceLogs"]:
            attrs = {}
            for attribute in resource_logs["resource"]["attributes"]:
                key = attribute["key"]
                if key in attrs:
                    raise ValueError("Duplicate resource attribute")
                attrs[key] = attribute["value"].get("stringValue")
            identity = tuple(
                attrs[key]
                for key in (
                    "service.name",
                    "service.instance.id",
                    "thesis.software.name",
                    "thesis.software.version",
                    "thesis.software.jar.sha256",
                )
            )
            for scope in resource_logs["scopeLogs"]:
                for record in scope["logRecords"]:
                    observed = int(record["observedTimeUnixNano"])
                    if not unix_nano(started_at) <= observed < unix_nano(finished_at):
                        raise ValueError("Observation outside this application execution")
                    observations.append(identity)
    if not observations or len(set(observations)) != 1:
        raise ValueError("Expected observations of exactly one application instance/JAR")
    service, instance, title, version, jar_hash = observations[0]
    document = json.loads(sbom.read_text(encoding="utf-8"))
    matches = [
        c
        for c in document.get("components", [])
        if (c.get("group"), c.get("name")) == ("org.apache.logging.log4j", "log4j-core")
    ]
    if len(matches) != 1:
        raise ValueError("Build SBOM must contain exactly one Log4j Core component")
    component = matches[0]
    hashes = [h["content"] for h in component.get("hashes", []) if h["alg"] == "SHA-256"]
    if hashes != [jar_hash]:
        raise ValueError("Loaded JAR hash differs from the build SBOM")
    case = TelemetryInput(
        service_name=service,
        service_instance_id=instance,
        package_name=title,
        start_time=started_at,
        end_time=finished_at,
        # Policy esplicita della demo: nessun attuatore di mitigazione disponibile.
        available_capabilities=[],
        prohibited_actions=[],
    )
    binding = AssetBinding(
        service_name=service, runtime_package=title, component_ref=component["bom-ref"]
    )
    select_component(
        document,
        binding,
        SupplyChainQuery(
            service_name=service,
            software={"package": title, "version": version, "evidence_id": "source-check"},
        ),
    )
    return (
        case,
        binding,
        {
            "loaded_version": version,
            "loaded_jar_sha256": jar_hash,
            "record_count": len(observations),
            "component_ref": component["bom-ref"],
        },
    )


def prepare(output, *, skip_build=False):
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=False)
    build_command = ["mvn", "-B", "-ntp", "package"]
    if not skip_build:
        with (output / "build.log").open("x") as log:
            subprocess.run(
                build_command,
                cwd=PROJECT,
                stdout=log,
                stderr=subprocess.STDOUT,
                check=True,
                timeout=600,
            )
    target = PROJECT / "target"
    # Copia immutabile della build eseguita, non soltanto una SBOM generata in passato.
    for original, name in (
        (target / "bom.json", "sbom.cdx.json"),
        (target / "observed-app-1.0.0.jar", "application.jar"),
        (PROJECT / "pom.xml", "pom.xml"),
    ):
        shutil.copyfile(original, output / name)
    classpath = (
        str(output / "application.jar")
        + os.pathsep
        + (target / "classpath.txt").read_text().strip()
    )
    command = [
        "java",
        "-cp",
        classpath,
        "it.poliba.thesis.ObservedApplication",
        str(output / "otel.jsonl"),
    ]
    started = datetime.now(UTC)
    with (output / "application.log").open("x") as log:
        subprocess.run(
            command, cwd=PROJECT, stdout=log, stderr=subprocess.STDOUT, check=True, timeout=30
        )
    finished = datetime.now(UTC)
    case, binding, observed = inspect_sources(
        output / "otel.jsonl", output / "sbom.cdx.json", started, finished
    )
    profile = json.loads((ROOT / "config/backends.cti-real.json").read_text())
    profile["telemetry"] = {
        "transport": "http",
        "url": "http://127.0.0.1:8004/v1/observations",
        "source_id": "observed-app-sdk",
        "acquisition": "sdk-file",
    }
    profile["countermeasure_input"] = {
        "transport": "http",
        "url": "http://127.0.0.1:8005/v1/enrichment",
        "expected_kind": "live",
        "source_id": "observed-app-build",
        "sbom_kind": "provided",
        "timeout_seconds": 300,
        "sbom_sha256": sha256(output / "sbom.cdx.json"),
    }
    settings = BackendSettings.model_validate(profile)
    manifest = {
        "status": "sources-validated",
        "application": "local-demonstration",
        "sbom_origin": "cyclonedx-maven-plugin:2.9.3",
        "telemetry_origin": "opentelemetry-java-sdk:1.66.0",
        "build_executed": not skip_build,
        "build_command": build_command,
        "application_command": command,
        "started_at": started.isoformat(),
        "finished_at": finished.isoformat(),
        **observed,
        "files": {
            name: sha256(output / name)
            for name in ("application.jar", "pom.xml", "sbom.cdx.json", "otel.jsonl")
        },
        "limitations": [
            "Finite demonstration workload, not production monitoring.",
            "Observed SDK logs only; no Collector, traces or metrics in this run.",
            "JAR/SBOM hash equality is checked by the demo harness, not remote attestation.",
            "Source preparation does not run CAMEL or an LLM.",
        ],
    }
    for name, payload in (
        ("input.json", case.model_dump(mode="json")),
        ("binding.json", binding.model_dump(mode="json")),
        ("backends.json", settings.model_dump(mode="json")),
        ("source_manifest.json", manifest),
    ):
        with (output / name).open("x", encoding="utf-8") as stream:
            json.dump(payload, stream, indent=2)
            stream.write("\n")
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--skip-build",
        action="store_true",
        help="Riusa la build locale; ricrea sempre osservazioni e istanza",
    )
    args = parser.parse_args()
    print(f"Sorgenti verificate: {prepare(args.output, skip_build=args.skip_build)}")


if __name__ == "__main__":
    main()
