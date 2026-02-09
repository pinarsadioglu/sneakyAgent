from __future__ import annotations

from pathlib import Path

from sneakyagent.agent.llm import LLMAdapter, NoopLLMAdapter
from sneakyagent.agent.mock import MockAgent
from sneakyagent.models import AgentOutput, AgentTask


class AgentRunner:
    def __init__(self, llm_adapter: LLMAdapter | None = None) -> None:
        self.llm_adapter = llm_adapter or NoopLLMAdapter()
        self.mock_agent = MockAgent()

    def run(self, repo_path: Path, task: AgentTask) -> AgentOutput:
        if task.mode == "llm":
            return self.llm_adapter.run(repo_path, task)
        return self.mock_agent.run(repo_path, task)
