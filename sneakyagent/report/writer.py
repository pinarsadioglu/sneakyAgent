from __future__ import annotations

import json
from dataclasses import asdict
from pathlib import Path
from typing import Dict, List, Optional

from sneakyagent.analyze.analyzer import Finding
from sneakyagent.utils import write_text


class ReportWriter:
    def to_json(self, findings: List[Finding]) -> str:
        payload = [asdict(f) for f in findings]
        return json.dumps(payload, indent=2, ensure_ascii=True)

    def to_markdown(
        self,
        findings: List[Finding],
        diff_findings: Optional[List[Finding]] = None,
    ) -> str:
        lines = ["# SneakyAgent Report", ""]

        if not findings and not diff_findings:
            lines.append("No findings.\n")
            return "\n".join(lines)

        if findings:
            lines.append("## Findings")
            lines.append("")
            by_sev = self._group_by_severity(findings)
            for sev in ["high", "medium", "low"]:
                items = by_sev.get(sev, [])
                if items:
                    lines.append(f"### {sev.upper()} ({len(items)})")
                    for f in items:
                        lines.append(f"- **{f.rule_id}**: {f.snippet}")
                    lines.append("")
        else:
            lines.append("## Findings\n\nNo findings.\n")

        if diff_findings:
            lines.append("## Drift Findings")
            lines.append("")
            by_sev = self._group_by_severity(diff_findings)
            for sev in ["high", "medium", "low"]:
                items = by_sev.get(sev, [])
                if items:
                    lines.append(f"### {sev.upper()} ({len(items)})")
                    for f in items:
                        lines.append(f"- **{f.rule_id}**: {f.snippet}")
                    lines.append("")
        else:
            lines.append("## Drift Findings\n\nNo drift findings.\n")

        return "\n".join(lines)

    def _group_by_severity(self, findings: List[Finding]) -> Dict[str, List[Finding]]:
        by_sev: Dict[str, List[Finding]] = {}
        for f in findings:
            by_sev.setdefault(f.severity, []).append(f)
        return by_sev

    def write(self, path: Path, content: str) -> None:
        write_text(path, content)
