from __future__ import annotations

from abc import ABC, abstractmethod
from typing import List

from sneakyagent.models import MutationPlan, ScanResult
from sneakyagent.poison.catalog import RuleCatalog


class Strategy(ABC):
    @abstractmethod
    def plan(
        self,
        scan: ScanResult,
        catalog: RuleCatalog,
        categories: List[str],
        intensity: str,
        allowed_layers: List[str],
    ) -> List[MutationPlan]:
        raise NotImplementedError
