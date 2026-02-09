from __future__ import annotations

from pathlib import Path
from typing import Iterable


class MutationOps:
    def apply_insert(self, path: Path, content: str, intensity: str) -> str | None:
        original = path.read_text(encoding="utf-8")
        if content.strip() in original:
            return None

        # Gate: code files are only mutated based on intensity + sensitivity
        if self._is_code(path):
            if intensity == "subtle" and not self._is_sensitive_code(path):
                return None
            # normal: allow sensitive code files, skip generic ones
            # strong: allow all code files

        payload = self._format_payload(path, content, intensity)
        if payload is None:
            return None

        if self._is_markdown(path):
            return original.rstrip() + "\n\n" + payload + "\n"

        if self._is_code_or_config(path):
            return payload + original

        return original.rstrip() + "\n" + payload + "\n"

    def apply_replace(
        self, path: Path, replacements: Iterable[tuple[str, str]], intensity: str
    ) -> str | None:
        original = path.read_text(encoding="utf-8")
        updated = original
        count = self._replacement_count(intensity)
        changes = 0
        for pattern, replacement in replacements:
            before = updated
            if count < 0:
                updated = updated.replace(pattern, replacement)
            else:
                updated = updated.replace(pattern, replacement, count)
            if updated != before:
                changes += 1
        if changes == 0:
            return None
        return updated

    def _format_payload(self, path: Path, content: str, intensity: str) -> str | None:
        content = self._trim_by_intensity(content, intensity)

        if self._is_markdown(path):
            return "## Context\n\n" + content

        if self._is_python(path):
            return self._comment_block("#", content)
        if self._is_js_ts(path):
            return self._comment_block("//", content)
        if self._is_terraform(path):
            return self._comment_block("#", content)
        if self._is_toml_yaml_env_docker(path):
            return self._comment_block("#", content)
        if self._is_json(path):
            return None

        return self._comment_block("#", content)

    def _trim_by_intensity(self, content: str, intensity: str) -> str:
        lines = [line.strip() for line in content.strip().splitlines() if line.strip()]
        if intensity == "subtle":
            return lines[0] if lines else ""
        if intensity == "strong":
            return "\n".join(lines)
        return "\n".join(lines[:2])

    def _replacement_count(self, intensity: str) -> int:
        if intensity == "subtle":
            return 1
        if intensity == "strong":
            return -1
        return 2

    def _comment_block(self, prefix: str, content: str) -> str:
        lines = [line.strip() for line in content.splitlines() if line.strip()]
        return "\n".join(f"{prefix} {line}" for line in lines) + "\n"

    def _is_markdown(self, path: Path) -> bool:
        return path.suffix.lower() == ".md"

    def _is_python(self, path: Path) -> bool:
        return path.suffix.lower() == ".py"

    def _is_js_ts(self, path: Path) -> bool:
        return path.suffix.lower() in {".js", ".ts", ".jsx", ".tsx"}

    def _is_terraform(self, path: Path) -> bool:
        return path.suffix.lower() in {".tf", ".hcl"}

    def _is_code(self, path: Path) -> bool:
        return self._is_python(path) or self._is_js_ts(path) or self._is_terraform(path)

    def _is_sensitive_code(self, path: Path) -> bool:
        name = path.name.lower()
        needles = (
            "auth", "security", "validator", "crypto", "session", "jwt",
            "security_group", "iam", "password", "network", "firewall",
            "acl", "policy", "encrypt", "ingress", "egress",
        )
        return any(token in name for token in needles)

    def _is_json(self, path: Path) -> bool:
        return path.suffix.lower() == ".json"

    def _is_toml_yaml_env_docker(self, path: Path) -> bool:
        return path.suffix.lower() in {".toml", ".yml", ".yaml", ".env"} or path.name in {
            "Dockerfile",
            "docker-compose.yml",
        }

    def _is_code_or_config(self, path: Path) -> bool:
        return (
            self._is_python(path)
            or self._is_js_ts(path)
            or self._is_terraform(path)
            or self._is_toml_yaml_env_docker(path)
        )
