from __future__ import annotations

from pathlib import Path
from typing import List

from sneakyagent.models import MutationPlan, ScanResult
from sneakyagent.poison.catalog import RuleCatalog
from sneakyagent.poison.strategy import Strategy


class HeuristicStrategy(Strategy):
    def plan(
        self,
        scan: ScanResult,
        catalog: RuleCatalog,
        categories: List[str],
        intensity: str,
        allowed_layers: List[str],
    ) -> List[MutationPlan]:
        templates = [
            t
            for t in catalog.by_category(categories)
            if t.layer in allowed_layers
        ]
        plans: List[MutationPlan] = []

        # subtle: 1 target per template, normal: up to 3, strong: all candidates
        if intensity == "subtle":
            limit = 1
        elif intensity == "strong":
            limit = None  # no limit
        else:
            limit = 3
        for template in templates:
            candidates = self._candidates(scan, template.layer, template.target_globs)
            selected = candidates if limit is None else candidates[:limit]
            for target in selected:
                plans.append(
                    MutationPlan(
                        template=template,
                        target_path=target,
                        intensity=intensity,
                    )
                )
        return plans

    def _candidates(self, scan: ScanResult, layer: str, globs: List[str]) -> List[Path]:
        layer_files = scan.layers.get(layer, [])
        if not globs:
            return list(layer_files)
        filtered: List[Path] = []
        for path in layer_files:
            for pattern in globs:
                if path.match(pattern):
                    filtered.append(path)
                    break
        return filtered
