"""Adattatore delimitato dei log Apache AIT: confronto esatto, nessuna estrazione LLM.

La configurazione è locale al gateway. Il MAS riceve soltanto riferimenti e
metadati validati; non legge i file della baseline o quelli dell'inventario.
"""

import argparse
import hashlib
import json
import re
from pathlib import Path

from pydantic import Field

from thesis_agents.schemas.base import Message, Text
from thesis_agents.schemas.telemetry_source import SHA256, RecordedApacheContext

# Solo il messaggio di avvio di mpm_prefork, non banner arbitrari o righe YAML.
STARTUP = re.compile(
    r"^\[(?P<time>[^\]\r\n]+)\] \[mpm_prefork:notice\] \[pid \d+\] "
    r"AH00163: Apache/(?P<version>\d+\.\d+\.\d+) \(Ubuntu\) "
    r"OpenSSL/[^\s]+ configured -- resuming normal operations$"
)


class SourceFile(Message):
    path: Text  # Configurazione server: non serializzata nella risposta HTTP.
    sha256: SHA256


class OriginalLog(SourceFile):
    member: str = Field(pattern=r"^gather/webserver/logs/apache2/error\.log(?:\.\d+)?$")


class ApacheBinding(Message):
    contract: str = Field(default="ait-apache-binding-v1", pattern=r"^ait-apache-binding-v1$")
    export_sha256: SHA256
    facts: SourceFile
    logs: list[OriginalLog] = Field(min_length=1, max_length=10)


def read_checked(file: SourceFile):
    with Path(file.path).open("rb") as stream:
        raw = stream.read(2 * 1024 * 1024 + 1)
    if len(raw) > 2 * 1024 * 1024 or hashlib.sha256(raw).hexdigest() != file.sha256:
        raise ValueError("Recorded source changed or exceeds size limit")
    return raw


class ApacheSource:
    def __init__(self, binding_path: Path, export_sha256: str):
        with binding_path.open("rb") as stream:
            raw = stream.read(65537)
        if len(raw) > 65536:
            raise ValueError("Binding too large")
        binding = ApacheBinding.model_validate_json(raw)
        if binding.export_sha256 != export_sha256:
            raise ValueError("Apache binding does not match export")
        if len({x.member for x in binding.logs}) != len(binding.logs):
            raise ValueError("Duplicate original log members")
        facts = json.loads(read_checked(binding.facts))
        package = facts["packages"]["apache2"]
        if (
            len(package) != 1
            or package != facts["ansible_facts"]["packages"]["apache2"]
            or facts["inventory_hostname"] != "webserver"
            or facts["ansible_hostname"] != "webserver"
            or facts["services"]["apache2"]["name"] != "apache2"
        ):
            raise ValueError("Inconsistent Apache inventory or host")
        package = package[0]
        if package["name"] != "apache2":
            raise ValueError("Wrong inventory package")
        self.context = RecordedApacheContext(
            dataset_url="https://zenodo.org/records/5789064",
            scenario="russellmitchell",
            host="webserver",
            fqdn=facts["ansible_fqdn"],
            export_sha256=export_sha256,
            binding_sha256=hashlib.sha256(raw).hexdigest(),
            facts_sha256=binding.facts.sha256,
            facts_collected_at=facts["ansible_date_time"]["iso8601"],
            distribution=facts["ansible_distribution"],
            distribution_version=facts["ansible_distribution_version"],
            distribution_release=facts["ansible_distribution_release"],
            package_version=package["version"],
            package_origin=package["origin"],
            package_manager=package["source"],
        )
        self.lines = {}
        for file in binding.logs:
            for number, line in enumerate(read_checked(file).decode().splitlines(), 1):
                if STARTUP.fullmatch(line):
                    self.lines.setdefault(line, []).append(
                        {
                            "file": file.member,
                            "sha256": file.sha256,
                            "line": number,
                        }
                    )

    def identify(self, resource, record):
        body = record.get("body", {}).get("stringValue", "")
        match = STARTUP.fullmatch(body)
        if match is None:
            return None
        # Questo adattatore tratta export privi di identità strumentata. Non
        # sostituisce service.name o altre attribuzioni già presenti nella risorsa.
        if resource.get("attributes"):
            raise ValueError("Recorded Apache binding cannot replace resource attributes")
        originals = self.lines.get(body, [])
        if len(originals) != 1:
            raise ValueError("Apache startup has no unique exact original log match")
        return {
            "service_name": self.context.service,
            "service_instance_id": self.context.scope_id,
            "package": "Apache",  # Nome letterale: nessun alias CTI implicito.
            "version": match["version"],
            "identity_basis": "recorded-apache-startup",
            "original_log": {**originals[0], "event_time_text": match["time"]},
        }


def prepare_binding(export: Path, members: Path, output: Path):
    """Fissa i file forniti dall'operatore; non scarica né attesta il dataset."""

    def source(path):
        with path.open("rb") as stream:
            data = stream.read(2 * 1024 * 1024 + 1)
        if len(data) > 2 * 1024 * 1024:
            raise ValueError("Original member too large")
        return {"path": str(path.resolve()), "sha256": hashlib.sha256(data).hexdigest()}

    with export.open("rb") as stream:
        raw = stream.read(16 * 1024 * 1024 + 1)
    if len(raw) > 16 * 1024 * 1024:
        raise ValueError("Export too large")
    binding = ApacheBinding(
        export_sha256=hashlib.sha256(raw).hexdigest(),
        facts=SourceFile(**source(members / "gather/webserver/facts.json")),
        logs=[
            OriginalLog(member=str(p.relative_to(members)), **source(p))
            for p in sorted((members / "gather/webserver/logs/apache2").glob("error.log*"))
            if p.is_file()
        ],
    )
    # La scrittura esclusiva impedisce di cambiare silenziosamente una fonte fissata.
    with output.open("x") as stream:
        stream.write(binding.model_dump_json(indent=2) + "\n")
    return binding


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--export", type=Path, required=True)
    parser.add_argument("--members", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    prepare_binding(args.export, args.members, args.output)
    print(f"Binding locale creato: {args.output}; verificare la provenienza dei file forniti.")


if __name__ == "__main__":
    main()
