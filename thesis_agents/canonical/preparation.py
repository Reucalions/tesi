"""Adapter del checkpoint MAS al generatore esterno configurato su costa-thesis."""

import hashlib
import json
import os
import subprocess
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator

from thesis_agents.canonical.contracts import (
    SHA256,
    CanonicalEdge,
    CanonicalGraph,
    PreparationArtifact,
    PreparationRequest,
)
from thesis_agents.mcp.client import digest
from thesis_agents.mcp.shared_contracts import RankRemediationsRequest, WireModel
from thesis_agents.schemas import CandidateStrategies, RuntimeEvidence, VulnerabilityReport


def bytes_digest(content: bytes) -> str:
    return hashlib.sha256(content).hexdigest()


class PreparationSettings(WireModel):
    contract: Literal["bottalico-preparation-process-v1"] = "bottalico-preparation-process-v1"
    repository: Path
    python: Path
    source_ontology: Path
    source_ontology_sha256: SHA256
    generator_manifest_sha256: SHA256
    knowledge_snapshot_id: str = Field(min_length=1)
    ranking_ontology_version: str | None = Field(default=None, min_length=1)
    timeout_seconds: float = Field(default=600, gt=0, le=1800, allow_inf_nan=False)

    @field_validator("repository", "python", "source_ontology")
    @classmethod
    def absolute_path(cls, value):
        if not value.is_absolute():
            raise ValueError("Preparation paths must be absolute and configured by the operator")
        return value

    @classmethod
    def load(cls, path):
        return cls.model_validate_json(path.read_text())


def validated_inputs(request: PreparationRequest, source_dir: Path) -> dict:
    """Rilegge byte e schemi originali prima di qualsiasi invocazione esterna."""
    schemas = {
        "runtime_evidence": RuntimeEvidence,
        "vulnerability_report": VulnerabilityReport,
        "candidate_strategies": CandidateStrategies,
    }
    inputs = {}
    for name, schema in schemas.items():
        raw = (source_dir / f"{name}.json").read_bytes()
        if bytes_digest(raw) != request.input_digests[name]:
            raise ValueError(f"Source artifact digest differs: {name}")
        inputs[name] = schema.model_validate_json(raw)
    evidence, report, candidates = (inputs[name] for name in schemas)
    if evidence.service_name != request.asset_id or report.asset_id != request.asset_id:
        raise ValueError("Preparation asset differs from published evidence/report")
    findings = {f.cve_id: f for f in report.vulnerabilities}
    entries = [
        (row.asset, entry)
        for row in request.assessments.results
        for match in row.matches
        for entry in match.affected_entries
    ]
    if set(findings) != {entry.cve_id for _, entry in entries}:
        raise ValueError("Preparation must cover exactly the confirmed MAS findings")
    observations = {(s.package, s.version, s.evidence_id) for s in evidence.software}
    for asset, entry in entries:
        finding = findings[entry.cve_id]
        if (asset.product, asset.version) != (finding.package, finding.observed_version) or any(
            (finding.package, finding.observed_version, identifier) not in observations
            for identifier in finding.evidence_ids
        ):
            raise ValueError("Assessment/finding differs from observed software evidence")
    expected = {
        (cve, candidate.id)
        for candidate in candidates.strategies
        for cve in candidate.addressed_vulnerabilities
    }
    if expected != {(b.cve_id, b.strategy_id) for b in request.bindings}:
        raise ValueError("Bindings must cover exactly all MAS candidate/CVE pairs")
    # A completed source run also supplies a durable correlation ID.
    provenance = source_dir / "provenance.json"
    if provenance.exists() and json.loads(provenance.read_text())["run_id"] != request.run_id:
        raise ValueError("Preparation run_id differs from source run provenance")
    return {name: value.model_dump(mode="json") for name, value in inputs.items()}


class GeneratorResponse(WireModel):
    graphs: dict[str, dict]
    observed_assets_owl: str = Field(min_length=1)
    aln_ontology: str = Field(min_length=1)
    source_ontology_sha256: SHA256
    generator_manifest_sha256: SHA256


def canonical_artifact(request, settings, raw):
    """Valida la topologia originale e conserva la mappa MAS -> individui KG."""
    response = GeneratorResponse.model_validate(raw)
    if (
        response.source_ontology_sha256 != settings.source_ontology_sha256
        or response.generator_manifest_sha256 != settings.generator_manifest_sha256
    ):
        raise ValueError("Generator response differs from configured source/installation")
    if set(response.graphs) != {b.cve_id for b in request.bindings}:
        raise ValueError("Generator graph coverage differs from request")
    graphs = []
    for cve, raw_graph in sorted(response.graphs.items()):
        names = sorted(b.ontology_individual for b in request.bindings if b.cve_id == cve)
        native = RankRemediationsRequest(
            cve_id=cve,
            candidates=[{"id": name, "name": name} for name in names],
            graph=raw_graph,
            knowledge_snapshot_id=settings.knowledge_snapshot_id,
            ontology_version=settings.ranking_ontology_version,
        )
        native.graph.nodes.sort(key=lambda n: (n.type, n.id))
        native.graph.edges.sort(key=lambda e: (e.source, e.target))
        graphs.append(
            CanonicalGraph(
                cve_id=cve,
                ranking_request=native,
                edge_sources=[
                    CanonicalEdge(
                        **{"from": edge.source, "to": edge.target},
                        origin="kg_remediation"
                        if edge.source == cve
                        else "generator_comparison_ring",
                    )
                    for edge in native.graph.edges
                ],
            )
        )
    artifact = PreparationArtifact(
        run_id=request.run_id,
        asset_id=request.asset_id,
        request_sha256=digest(request.model_dump(mode="json", exclude_none=True)),
        input_digests=request.input_digests,
        knowledge_snapshot_id=settings.knowledge_snapshot_id,
        source_ontology_sha256=settings.source_ontology_sha256,
        generator_manifest_sha256=settings.generator_manifest_sha256,
        observed_assets_sha256=bytes_digest(response.observed_assets_owl.encode()),
        aln_ontology_sha256=bytes_digest(response.aln_ontology.encode()),
        bindings=sorted(request.bindings, key=lambda b: (b.cve_id, b.strategy_id)),
        graphs=graphs,
    )
    return artifact, response


class ExternalPreparationTool:
    def __init__(self, settings: PreparationSettings):
        self.settings = PreparationSettings.model_validate(settings.model_dump())

    def prepare(self, request, output_dir):
        settings = self.settings
        root = settings.repository / "app/semantic_preparation"
        manifest = root / "installation-manifest.json"
        if bytes_digest(manifest.read_bytes()) != settings.generator_manifest_sha256:
            raise ValueError("Generator installation is not the configured version")
        branch = subprocess.check_output(
            ["git", "branch", "--show-current"], cwd=settings.repository, text=True
        ).strip()
        if branch != "costa-thesis":
            raise ValueError("External generator requires branch costa-thesis")
        # All arguments come from operator settings; the agent calls a zero-argument tool.
        command = [
            str(settings.python),
            str(root / "runner.py"),
            "--ontology",
            str(settings.source_ontology),
            "--ontology-sha256",
            settings.source_ontology_sha256,
            "--manifest-sha256",
            settings.generator_manifest_sha256,
        ]
        with (output_dir / "generator.stderr.log").open("x") as error_log:
            try:
                result = subprocess.run(
                    command,
                    input=request.model_dump_json(exclude_none=True),
                    stdout=subprocess.PIPE,
                    stderr=error_log,
                    text=True,
                    cwd=settings.repository,
                    timeout=settings.timeout_seconds,
                    check=False,
                    env={
                        "PATH": os.defpath,
                        "PYTHONIOENCODING": "utf-8",
                        "PYTHONDONTWRITEBYTECODE": "1",
                    },
                )
            except subprocess.TimeoutExpired as exc:
                partial = exc.stdout or b""
                if isinstance(partial, bytes):
                    partial = partial.decode("utf-8", errors="replace")
                (output_dir / "generator-response.json").write_text(partial)
                raise RuntimeError("External preparation timed out; process terminated") from None
        # Preserve raw response even if malformed; it is never published as a valid artifact.
        (output_dir / "generator-response.json").write_text(result.stdout)
        if result.returncode:
            raise RuntimeError("External preparation failed; inspect generator.stderr.log")
        envelope = json.loads(result.stdout)
        if (
            set(envelope) != {"ok", "action", "payload"}
            or envelope["ok"] is not True
            or envelope["action"] != "prepare_argumentation"
        ):
            raise ValueError("Invalid generator envelope")
        return canonical_artifact(request, settings, envelope["payload"])
