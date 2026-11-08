"""Pubblicazione del checkpoint canonico su input MAS gia validati e immutabili."""

import copy
import json
import time
from pathlib import Path

from thesis_agents.canonical.contracts import PreparationArtifact, PreparationRequest
from thesis_agents.canonical.preparation import (
    ExternalPreparationTool,
    PreparationSettings,
    bytes_digest,
    validated_inputs,
)
from thesis_agents.mcp.client import digest


class PreparationSession:
    def __init__(self, source_dir, output_dir, request, settings):
        self.source_dir = Path(source_dir)
        self.output_dir = Path(output_dir)
        self.request = PreparationRequest.model_validate(request.model_dump())
        self.settings = PreparationSettings.model_validate(settings.model_dump())
        self.inputs = validated_inputs(self.request, self.source_dir)
        self.output_dir.mkdir(parents=True, exist_ok=False)
        self._artifact = None
        (self.output_dir / "request.json").write_text(self.request.model_dump_json(indent=2) + "\n")
        (self.output_dir / "profile.json").write_text(
            self.settings.model_dump_json(indent=2) + "\n"
        )
        inputs = self.output_dir / "inputs"
        inputs.mkdir()
        for name in self.inputs:
            (inputs / f"{name}.json").write_bytes((self.source_dir / f"{name}.json").read_bytes())

    def get_context(self) -> dict:
        """Read the three separate MAS artifacts and the configured preparation scope.

        Returns:
            dict: Producer artifacts and explicit bindings; no editable generator arguments.
        """
        validated_inputs(self.request, self.source_dir)
        return {
            "run_id": self.request.run_id,
            "artifacts": copy.deepcopy(self.inputs),
            "preparation": self.request.model_dump(mode="json"),
            "outputs": ["canonical_preparation"],
            "published": self._artifact is not None,
        }

    def prepare_argumentation(self) -> dict:
        """Run the configured Bottalico modules and publish canonical_preparation.

        Returns:
            dict: Validated per-CVE graphs, native ranking requests and source digests.
        """
        validated_inputs(self.request, self.source_dir)
        validated_inputs(self.request, self.output_dir / "inputs")
        if self._artifact is not None:
            return self.assert_complete().model_dump(mode="json", by_alias=True)
        started = time.monotonic()
        event = {
            "tool": "prepare_argumentation",
            "request_sha256": digest(self.request.model_dump(mode="json", exclude_none=True)),
        }
        try:
            result = self._generate()
            event["status"] = "validated"
            return result
        except BaseException as exc:
            event.update(status="failed", error_type=type(exc).__name__)
            raise
        finally:
            event["elapsed_seconds"] = time.monotonic() - started
            with (self.output_dir / "preparation_events.jsonl").open("a") as stream:
                stream.write(json.dumps(event) + "\n")

    def _generate(self):
        artifact, response = ExternalPreparationTool(self.settings).prepare(
            self.request, self.output_dir
        )
        validated_inputs(self.request, self.source_dir)
        validated_inputs(self.request, self.output_dir / "inputs")
        (self.output_dir / "observed_assets.owl").write_text(response.observed_assets_owl)
        (self.output_dir / "aln_ontology.owl").write_text(response.aln_ontology)
        native_requests = self.output_dir / "ranking-requests"
        native_requests.mkdir()
        for graph in artifact.graphs:
            with (native_requests / f"{graph.cve_id}.json").open("x") as stream:
                stream.write(json.dumps(graph.ranking_request.wire_payload(), indent=2) + "\n")
        # The artifact is the final commit marker; failed subprocesses leave diagnostics only.
        with (self.output_dir / "canonical_preparation.json").open("x") as stream:
            stream.write(artifact.model_dump_json(indent=2, by_alias=True) + "\n")
        self._artifact = artifact.model_copy(deep=True)
        return self.assert_complete().model_dump(mode="json", by_alias=True)

    def assert_complete(self) -> PreparationArtifact:
        if self._artifact is None:
            raise ValueError("canonical_preparation is unpublished")
        stored = PreparationArtifact.model_validate_json(
            (self.output_dir / "canonical_preparation.json").read_text()
        )
        if stored != self._artifact:
            raise ValueError("Published canonical preparation changed")
        if stored.request_sha256 != digest(self.request.model_dump(mode="json", exclude_none=True)):
            raise ValueError("Preparation request changed after publication")
        for name, expected in (
            ("observed_assets.owl", stored.observed_assets_sha256),
            ("aln_ontology.owl", stored.aln_ontology_sha256),
        ):
            if bytes_digest((self.output_dir / name).read_bytes()) != expected:
                raise ValueError("Published semantic artifact changed")
        for graph in stored.graphs:
            native = self.output_dir / "ranking-requests" / f"{graph.cve_id}.json"
            if json.loads(native.read_text()) != graph.ranking_request.wire_payload():
                raise ValueError("Exported native request changed")
        validated_inputs(self.request, self.source_dir)
        validated_inputs(self.request, self.output_dir / "inputs")
        return stored


def load_request(path):
    return PreparationRequest.model_validate_json(Path(path).read_text())


def load_prepared_checkpoint(directory):
    """Read an archived preparation without requiring the original generator or KG."""
    directory = Path(directory)
    artifact = PreparationArtifact.model_validate_json(
        (directory / "canonical_preparation.json").read_bytes()
    )
    request = load_request(directory / "request.json")
    settings = PreparationSettings.load(directory / "profile.json")
    if (
        artifact.request_sha256 != digest(request.model_dump(mode="json", exclude_none=True))
        or artifact.run_id != request.run_id
        or artifact.asset_id != request.asset_id
        or artifact.input_digests != request.input_digests
        or sorted(artifact.bindings, key=lambda b: (b.cve_id, b.strategy_id))
        != sorted(request.bindings, key=lambda b: (b.cve_id, b.strategy_id))
        or artifact.source_ontology_sha256 != settings.source_ontology_sha256
        or artifact.generator_manifest_sha256 != settings.generator_manifest_sha256
        or artifact.knowledge_snapshot_id != settings.knowledge_snapshot_id
    ):
        raise ValueError("Preparation differs from its request/profile")
    inputs = validated_inputs(request, directory / "inputs")
    for name, expected in (
        ("observed_assets.owl", artifact.observed_assets_sha256),
        ("aln_ontology.owl", artifact.aln_ontology_sha256),
    ):
        if bytes_digest((directory / name).read_bytes()) != expected:
            raise ValueError("Published semantic artifact changed")
    for graph in artifact.graphs:
        native = directory / "ranking-requests" / f"{graph.cve_id}.json"
        if json.loads(native.read_bytes()) != graph.ranking_request.wire_payload():
            raise ValueError("Exported native request changed")
    return artifact, inputs
