from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, List

from sneakyagent.models import FileMutation, MutationPlan
from sneakyagent.poison.llm import NoopPoisonLLMAdapter, PoisonLLMAdapter
from sneakyagent.poison.mutations import MutationOps

logger = logging.getLogger("sneakyagent")


class PatchApplier:
    def __init__(self, llm_adapter: PoisonLLMAdapter | None = None) -> None:
        self.mutations = MutationOps()
        self.llm_adapter = llm_adapter or NoopPoisonLLMAdapter()

    def apply(
        self, plans: List[MutationPlan], use_llm: bool = False
    ) -> List[FileMutation]:
        results: List[FileMutation] = []
        # Track original content for files touched multiple times
        originals: Dict[Path, str] = {}

        for plan in plans:
            target = plan.target_path
            template = plan.template

            # Capture original content before first mutation
            if target not in originals:
                try:
                    originals[target] = target.read_text(encoding="utf-8")
                except (OSError, PermissionError) as exc:
                    logger.warning("Cannot read %s: %s", target, exc)
                    continue

            if template.action == "replace":
                replacements = [
                    (rule.pattern, rule.replacement)
                    for rule in template.replacements
                ]
                after = self.mutations.apply_replace(
                    target, replacements, plan.intensity
                )
            else:
                content = template.content
                if use_llm:
                    try:
                        content = self.llm_adapter.generate(
                            template, target, plan.intensity
                        )
                    except Exception as exc:
                        logger.warning("LLM generation failed for %s: %s", target, exc)
                        # Fall back to template content
                after = self.mutations.apply_insert(
                    target, content, plan.intensity
                )

            if after is None:
                logger.debug("Skipped mutation %s on %s (no change)", template.id, target)
                continue

            before = target.read_text(encoding="utf-8")
            try:
                target.write_text(after, encoding="utf-8")
            except (OSError, PermissionError) as exc:
                logger.warning("Cannot write %s: %s", target, exc)
                continue

            results.append(
                FileMutation(
                    target_path=target,
                    before=originals[target],  # Always use the TRUE original
                    after=after,
                    template_id=plan.template.id,
                )
            )
        return results
