from __future__ import annotations

import random
from pathlib import Path
from typing import Dict, List, Tuple

from sneakyagent.models import MutationPlan, ScanResult
from sneakyagent.poison.catalog import RuleCatalog
from sneakyagent.poison.strategy import Strategy


class GeneticStrategy(Strategy):
    def __init__(
        self,
        population_size: int = 20,
        generations: int = 15,
        seed: int | None = None,
        mutation_rate: float = 0.4,
    ) -> None:
        self.population_size = population_size
        self.generations = generations
        self.mutation_rate = mutation_rate
        self.random = random.Random(seed)  # None = truly random

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
        if not templates:
            return []

        target_map = self._build_target_map(scan, templates)
        if not target_map:
            return []

        population = [
            self._random_individual(templates, target_map, intensity)
            for _ in range(self.population_size)
        ]

        for _ in range(self.generations):
            scored = [(self._fitness(ind, intensity), ind) for ind in population]
            scored.sort(key=lambda x: x[0], reverse=True)
            elite_count = max(2, self.population_size // 4)
            elites = [ind for _, ind in scored[:elite_count]]

            offspring: List[List[MutationPlan]] = []
            while len(offspring) + len(elites) < self.population_size:
                parent_a = self._tournament(scored)
                parent_b = self._tournament(scored)
                child = self._crossover(parent_a, parent_b)
                child = self._mutate(child, templates, target_map, intensity)
                offspring.append(child)

            population = elites + offspring

        best = max(population, key=lambda p: self._fitness(p, intensity), default=[])
        return best

    def _build_target_map(
        self, scan: ScanResult, templates: List
    ) -> Dict[str, List[Path]]:
        target_map: Dict[str, List[Path]] = {}
        for tmpl in templates:
            candidates = scan.layers.get(tmpl.layer, [])
            filtered: List[Path] = []
            for path in candidates:
                if any(path.match(pat) for pat in tmpl.target_globs):
                    filtered.append(path)
            if filtered:
                target_map[tmpl.id] = filtered
        return target_map

    def _random_individual(
        self,
        templates: List,
        target_map: Dict[str, List[Path]],
        intensity: str,
    ) -> List[MutationPlan]:
        plans: List[MutationPlan] = []
        for tmpl in templates:
            targets = target_map.get(tmpl.id, [])
            if not targets:
                continue
            # Randomly include or exclude each template for diversity
            if self.random.random() < 0.7:
                chosen = self.random.choice(targets)
                plans.append(
                    MutationPlan(template=tmpl, target_path=chosen, intensity=intensity)
                )
        return plans

    def _fitness(self, plans: List[MutationPlan], intensity: str = "normal") -> float:
        if not plans:
            return 0.0
        layer_weights = {
            "ai_instructions": 3.0,
            "documentation": 2.0,
            "configuration": 1.5,
            "infrastructure": 2.5,
            "templates": 1.0,
            "tooling": 0.8,
            "code_metadata": 1.2,
        }

        # Base score: sum of layer weights
        score = sum(layer_weights.get(p.template.layer, 1.0) for p in plans)

        # Category diversity bonus: more categories covered = better
        unique_categories = {p.template.category for p in plans}
        score += len(unique_categories) * 1.5

        # Layer diversity bonus
        unique_layers = {p.template.layer for p in plans}
        score += len(unique_layers) * 1.0

        # Stealth penalty: varies by intensity
        unique_files = {p.target_path for p in plans}
        if intensity == "subtle":
            stealth_threshold = 2
            penalty_weight = 1.0
        elif intensity == "strong":
            stealth_threshold = 8
            penalty_weight = 0.2
        else:
            stealth_threshold = 4
            penalty_weight = 0.5
        stealth_penalty = max(0, len(unique_files) - stealth_threshold) * penalty_weight
        score -= stealth_penalty

        # Concentration bonus: multiple mutations in same high-value file
        file_counts: Dict[Path, int] = {}
        for p in plans:
            file_counts[p.target_path] = file_counts.get(p.target_path, 0) + 1
        for path, count in file_counts.items():
            if count > 1:
                score += (count - 1) * 0.3

        return score

    def _tournament(self, scored: List[Tuple[float, List[MutationPlan]]]) -> List[MutationPlan]:
        k = min(4, len(scored))
        contenders = self.random.sample(scored, k=k)
        contenders.sort(key=lambda x: x[0], reverse=True)
        return contenders[0][1]

    def _crossover(
        self, a: List[MutationPlan], b: List[MutationPlan]
    ) -> List[MutationPlan]:
        # Uniform crossover: pick each gene from either parent
        max_len = max(len(a), len(b))
        child: List[MutationPlan] = []
        for i in range(max_len):
            if i < len(a) and i < len(b):
                child.append(a[i] if self.random.random() < 0.5 else b[i])
            elif i < len(a):
                if self.random.random() < 0.5:
                    child.append(a[i])
            else:
                if self.random.random() < 0.5:
                    child.append(b[i])
        return child

    def _mutate(
        self,
        plans: List[MutationPlan],
        templates: List,
        target_map: Dict[str, List[Path]],
        intensity: str,
    ) -> List[MutationPlan]:
        if not plans or self.random.random() > self.mutation_rate:
            return plans
        plans = list(plans)  # copy to avoid mutating parent

        # Either swap a target, add a new template, or remove one
        action = self.random.choice(["swap", "add", "remove"])

        if action == "swap" and plans:
            idx = self.random.randrange(len(plans))
            tmpl = plans[idx].template
            targets = target_map.get(tmpl.id, [])
            if targets:
                plans[idx] = MutationPlan(
                    template=tmpl,
                    target_path=self.random.choice(targets),
                    intensity=intensity,
                )
        elif action == "add":
            available = [t for t in templates if t.id in target_map]
            if available:
                tmpl = self.random.choice(available)
                targets = target_map[tmpl.id]
                plans.append(
                    MutationPlan(
                        template=tmpl,
                        target_path=self.random.choice(targets),
                        intensity=intensity,
                    )
                )
        elif action == "remove" and len(plans) > 1:
            idx = self.random.randrange(len(plans))
            plans.pop(idx)

        return plans
