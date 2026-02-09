from __future__ import annotations

from pathlib import Path
from typing import Dict, Iterable, List

from sneakyagent.models import ScanResult


class RepoScanner:
    DEFAULT_IGNORES = {
        ".git",
        ".hg",
        ".svn",
        ".idea",
        ".vscode",
        "node_modules",
        "dist",
        "build",
        ".venv",
        "venv",
        "__pycache__",
    }

    LAYER_GLOBS: Dict[str, List[str]] = {
        "ai_instructions": [
            ".cursorrules",
            "CLAUDE.md",
            "AGENTS.md",
            ".github/copilot-instructions.md",
            ".windsurfrules",
            ".cursor/rules/*",
            ".cursor/prompts/*",
            ".cursor/tool-configs/*",
        ],
        "templates": [
            ".github/pull_request_template.md",
            ".github/ISSUE_TEMPLATE/*",
        ],
        "documentation": [
            "README.md",
            "CONTRIBUTING.md",
            "SECURITY.md",
            "docs/**/*.md",
            "adr/**/*.md",
        ],
        "configuration": [
            "pyproject.toml",
            "package.json",
            "Dockerfile",
            "docker-compose.yml",
            ".env",
            "Makefile",
        ],
        "tooling": [
            ".github/workflows/*",
            ".gitlab-ci.yml",
            "Makefile",
            "scripts/**/*",
        ],
        "infrastructure": [
            "**/*.tf",
            "**/*.hcl",
            "terraform/**/*",
            "infra/**/*",
            "docker-compose*.yml",
            "docker-compose*.yaml",
            "Dockerfile*",
            "k8s/**/*.yaml",
            "k8s/**/*.yml",
            "kubernetes/**/*.yaml",
            "kubernetes/**/*.yml",
            "helm/**/*.yaml",
            ".aws/**/*",
            "aws/**/*",
            "cloudformation/**/*.yaml",
            "cloudformation/**/*.json",
            "ansible/**/*.yml",
            "ansible/**/*.yaml",
        ],
        "code_metadata": [
            "**/*.py",
            "**/*.js",
            "**/*.ts",
            "**/*.go",
            "**/*.java",
            "**/*.rs",
            "**/*.rb",
        ],
    }

    def scan(self, repo_path: Path) -> ScanResult:
        layers: Dict[str, List[Path]] = {k: [] for k in self.LAYER_GLOBS}
        for path in self._iter_files(repo_path):
            relative = path.relative_to(repo_path)
            for layer, patterns in self.LAYER_GLOBS.items():
                if any(relative.match(p) for p in patterns):
                    layers[layer].append(path)
        return ScanResult(repo_path=repo_path, layers=layers)

    def _iter_files(self, root: Path) -> Iterable[Path]:
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            if any(part in self.DEFAULT_IGNORES for part in path.parts):
                continue
            yield path
