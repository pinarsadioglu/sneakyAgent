from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from sneakyagent.models import AgentOutput, AgentTask


class MockAgent:
    """Offline agent that reads the repo context and generates a realistic
    simulated output.  Unlike a real LLM, it echoes back the content of
    context-layer files so the analyzer can detect injected mutations."""

    CONTEXT_GLOBS: List[str] = [
        ".cursorrules",
        "CLAUDE.md",
        "AGENTS.md",
        ".github/copilot-instructions.md",
        ".windsurfrules",
        ".cursor/rules/*",
        "README.md",
        "CONTRIBUTING.md",
        "SECURITY.md",
        "docs/**/*.md",
        "Dockerfile*",
        "docker-compose*.yml",
        "docker-compose*.yaml",
        "**/*.tf",
        "**/*.hcl",
        "k8s/**/*.yaml",
        "k8s/**/*.yml",
        "kubernetes/**/*.yaml",
        "kubernetes/**/*.yml",
        "pyproject.toml",
        "package.json",
    ]

    IGNORE_DIRS = {
        ".git", ".hg", ".svn", "node_modules", "dist", "build",
        ".venv", "venv", "__pycache__", ".sneakyagent",
    }

    MAX_FILE_CHARS = 4000
    MAX_TOTAL_CHARS = 50000

    def run(self, repo_path: Path, task: AgentTask) -> AgentOutput:
        context_files = self._collect_context(repo_path)
        sections: List[str] = [
            "# Mock Agent Output",
            f"Task: {task.task}",
            f"Repo: {repo_path}",
            f"Context files found: {len(context_files)}",
            "",
        ]

        total = 0
        included = 0
        for rel_path, content in sorted(context_files.items()):
            header = f"--- {rel_path} ---"
            trimmed = content[: self.MAX_FILE_CHARS]
            if len(content) > self.MAX_FILE_CHARS:
                trimmed += f"\n... (truncated, {len(content)} chars total)"
            section = f"{header}\n{trimmed}\n"
            if total + len(section) > self.MAX_TOTAL_CHARS:
                remaining = len(context_files) - included
                sections.append(f"... ({remaining} more files omitted, total limit reached)")
                break
            sections.append(section)
            total += len(section)
            included += 1

        combined = "\n".join(sections)
        return AgentOutput(run_id="mock", content=combined, meta={"mode": "offline"})

    def _collect_context(self, repo_path: Path) -> Dict[str, str]:
        results: Dict[str, str] = {}
        for fpath in self._iter_files(repo_path):
            relative = fpath.relative_to(repo_path)
            if any(relative.match(pat) for pat in self.CONTEXT_GLOBS):
                try:
                    text = fpath.read_text(encoding="utf-8", errors="ignore")
                    results[str(relative)] = text
                except (OSError, PermissionError):
                    continue
        return results

    def _iter_files(self, root: Path):
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            if any(part in self.IGNORE_DIRS for part in path.parts):
                continue
            yield path
