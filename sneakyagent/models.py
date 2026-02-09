from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class ScanResult:
    repo_path: Path
    layers: Dict[str, List[Path]] = field(default_factory=dict)


@dataclass
class InsertTemplate:
    id: str
    layer: str
    category: str
    target_globs: List[str]
    content: str
    action: str = "insert"
    replacements: List["ReplacementRule"] = field(default_factory=list)


@dataclass
class ReplacementRule:
    pattern: str
    replacement: str


@dataclass
class MutationPlan:
    template: InsertTemplate
    target_path: Path
    intensity: str


@dataclass
class FileMutation:
    target_path: Path
    before: str
    after: str
    template_id: str


@dataclass
class RunManifest:
    run_id: str
    repo_path: Path
    created_at: str
    strategy: str
    categories: List[str]
    intensity: str
    layer_level: int
    mutations: List[FileMutation] = field(default_factory=list)
    meta: Dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentTask:
    task: str
    mode: str
    model: Optional[str] = None
    provider: Optional[str] = None


@dataclass
class AgentOutput:
    run_id: str
    content: str
    meta: Dict[str, Any] = field(default_factory=dict)
