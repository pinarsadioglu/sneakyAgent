from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List

import yaml

from sneakyagent.models import InsertTemplate, ReplacementRule

logger = logging.getLogger(__name__)

REQUIRED_TEMPLATE_FIELDS = {"id", "layer", "category", "target_globs", "content"}
VALID_ACTIONS = {"insert", "replace"}
VALID_LAYERS = {
    "ai_instructions",
    "documentation",
    "configuration",
    "infrastructure",
    "templates",
    "tooling",
    "code_metadata",
}


@dataclass
class RuleCatalog:
    templates: List[InsertTemplate]

    @classmethod
    def load_default(cls) -> "RuleCatalog":
        data_path = Path(__file__).resolve().parent.parent / "data" / "rules.yaml"
        return cls.load_from_path(data_path)

    @classmethod
    def load_from_path(cls, path: Path) -> "RuleCatalog":
        try:
            raw = yaml.safe_load(path.read_text(encoding="utf-8"))
        except yaml.YAMLError as e:
            raise ValueError(
                f"YAML parse hatası '{path}': {e}\n"
                "İpucu: Indentation tutarlılığını kontrol edin (2-space önerilir)."
            ) from e
        except OSError as e:
            raise FileNotFoundError(
                f"Rules dosyası bulunamadı: {path}"
            ) from e

        if not isinstance(raw, dict) or "templates" not in raw:
            raise ValueError(
                f"Geçersiz rules dosyası '{path}': "
                "Üst düzey 'templates' anahtarı gerekli."
            )

        raw_templates = raw["templates"]
        if not isinstance(raw_templates, list):
            raise ValueError(
                f"Geçersiz rules dosyası '{path}': "
                "'templates' bir liste olmalı."
            )

        templates: List[InsertTemplate] = []
        for idx, item in enumerate(raw_templates):
            if not isinstance(item, dict):
                logger.warning(
                    "Template #%d dict değil, atlanıyor: %r", idx, item
                )
                continue

            # --- gerekli alan kontrolü ---
            missing = REQUIRED_TEMPLATE_FIELDS - item.keys()
            if missing:
                raise ValueError(
                    f"Template #{idx} (id={item.get('id', '?')}): "
                    f"zorunlu alanlar eksik: {', '.join(sorted(missing))}"
                )

            # --- action doğrulama ---
            action = item.get("action", "insert")
            if action not in VALID_ACTIONS:
                raise ValueError(
                    f"Template '{item['id']}': "
                    f"geçersiz action '{action}', "
                    f"beklenen: {VALID_ACTIONS}"
                )

            # --- layer doğrulama ---
            layer = item["layer"]
            if layer not in VALID_LAYERS:
                logger.warning(
                    "Template '%s': bilinmeyen layer '%s'. "
                    "Bilinen layer'lar: %s",
                    item["id"],
                    layer,
                    ", ".join(sorted(VALID_LAYERS)),
                )

            # --- target_globs doğrulama ---
            tg = item["target_globs"]
            if not isinstance(tg, list) or not tg:
                raise ValueError(
                    f"Template '{item['id']}': "
                    "target_globs boş olmayan bir liste olmalı."
                )

            # --- replace action için replacements kontrolü ---
            if action == "replace":
                reps = item.get("replacements")
                if not reps:
                    raise ValueError(
                        f"Template '{item['id']}': "
                        "action='replace' ise en az bir replacement gerekli."
                    )
                for ri, rule in enumerate(reps):
                    for field in ("pattern", "replacement"):
                        if field not in rule:
                            raise ValueError(
                                f"Template '{item['id']}' replacement #{ri}: "
                                f"'{field}' alanı eksik."
                            )

            # --- nesne oluştur ---
            replacements: List[ReplacementRule] = []
            for rule in item.get("replacements", []) or []:
                replacements.append(
                    ReplacementRule(
                        pattern=rule["pattern"],
                        replacement=rule["replacement"],
                    )
                )
            templates.append(
                InsertTemplate(
                    id=item["id"],
                    layer=layer,
                    category=item["category"],
                    target_globs=tg,
                    content=item["content"],
                    action=action,
                    replacements=replacements,
                )
            )

        logger.info(
            "Katalog yüklendi: %d template (%s)",
            len(templates),
            path.name,
        )
        return cls(templates=templates)

    def by_category(self, categories: List[str]) -> List[InsertTemplate]:
        if not categories:
            return self.templates
        return [t for t in self.templates if t.category in categories]

    def by_layer(self, layer: str) -> List[InsertTemplate]:
        return [t for t in self.templates if t.layer == layer]
