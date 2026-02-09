from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import List

from sneakyagent.models import FileMutation, RunManifest
from sneakyagent.utils import ensure_dir, write_json, write_text


class RunStore:
    def __init__(self, repo_path: Path, run_id: str) -> None:
        self.repo_path = repo_path
        self.run_id = run_id
        self.base_dir = repo_path / ".sneakyagent" / "runs" / run_id
        self.backup_dir = self.base_dir / "backup"
        self.artifacts_dir = self.base_dir / "artifacts"
        ensure_dir(self.backup_dir)
        ensure_dir(self.artifacts_dir)

    def save_manifest(self, manifest: RunManifest) -> None:
        manifest_path = self.base_dir / "manifest.json"
        payload = asdict(manifest)
        payload["repo_path"] = str(manifest.repo_path)
        payload["mutations"] = [
            {
                "target_path": str(m.target_path),
                "template_id": m.template_id,
                "before_sha256": self._sha(m.before),
                "after_sha256": self._sha(m.after),
            }
            for m in manifest.mutations
        ]
        write_json(manifest_path, payload)

    def save_backups(self, mutations: List[FileMutation]) -> None:
        for mutation in mutations:
            relative = mutation.target_path.relative_to(self.repo_path)
            backup_path = self.backup_dir / relative
            ensure_dir(backup_path.parent)
            write_text(backup_path, mutation.before)

    def save_artifact(self, name: str, content: str) -> None:
        path = self.artifacts_dir / name
        write_text(path, content)

    def load_manifest(self) -> dict:
        manifest_path = self.base_dir / "manifest.json"
        return json.loads(manifest_path.read_text(encoding="utf-8"))

    def _sha(self, content: str) -> str:
        import hashlib

        return hashlib.sha256(content.encode("utf-8")).hexdigest()
