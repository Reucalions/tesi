"""Verify the frozen final result bundle and reproduce its tables without services."""

from __future__ import annotations

import hashlib
import json
import shutil
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
BUNDLE = ROOT / "evaluation/final-results-v1"


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def verify():
    manifest = json.loads((BUNDLE / "manifest.json").read_text())
    for relative, expected in manifest.items():
        path = BUNDLE / relative
        if path.parent != BUNDLE or not path.is_file() or sha(path) != expected:
            raise ValueError(f"Bundle hash mismatch: {relative}")
    with tempfile.TemporaryDirectory(prefix="tesi-final-replay-") as directory:
        work = Path(directory)
        evidence = work / "inputs"
        with tarfile.open(BUNDLE / "source-inputs.tar.gz", "r:gz") as archive:
            names = set()
            for member in archive:
                relative = PurePosixPath(member.name)
                if (
                    not member.isfile()
                    or relative.is_absolute()
                    or ".." in relative.parts
                    or member.name in names
                ):
                    raise ValueError(f"Unsafe or duplicate archived path: {member.name}")
                names.add(member.name)
                path = evidence / member.name
                path.parent.mkdir(parents=True, exist_ok=True)
                with archive.extractfile(member) as source, path.open("wb") as target:
                    shutil.copyfileobj(source, target)
        inputs = json.loads((BUNDLE / "input-manifest.json").read_text())
        for relative, expected in inputs.items():
            if sha(evidence / relative) != expected:
                raise ValueError(f"Input hash mismatch: {relative}")
        output = work / "recomputed"
        subprocess.run(
            [
                sys.executable,
                str(ROOT / "evaluation/consolidate_final.py"),
                "--evidence-root",
                str(evidence),
                "--output",
                str(output),
                "--inventory-snapshot",
                str(BUNDLE / "inventory.json"),
            ],
            check=True,
        )
        compared = []
        for path in sorted(output.iterdir()):
            expected = BUNDLE / path.name
            if not expected.exists() or path.read_bytes() != expected.read_bytes():
                # Each bundle has a different set of documentation/protocol files.
                if path.name == "manifest.json":
                    continue
                raise ValueError(f"Recomputed artifact differs: {path.name}")
            compared.append(path.name)
        print(
            json.dumps(
                {
                    "bundle_files_verified": len(manifest),
                    "archived_inputs_verified": len(inputs),
                    "recomputed_artifacts_equal": compared,
                    "network_or_ledger_access": False,
                }
            )
        )


if __name__ == "__main__":
    verify()
