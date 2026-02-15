## Architecture Overview

SneakyAgent is organized around a scan → plan → apply → simulate → analyze pipeline.
Each step is modular so you can swap strategy, templates, or agent backends.

### Pipeline

1. Scan
   - `scanner` walks the repo and builds a layer map.
   - Layers include AI instructions, docs, config, templates, tooling, code metadata.

2. Plan
   - `poison` strategies select templates based on category, intensity, and layer scope.
   - `heuristic` is deterministic and lightweight.
   - `ga` uses a genetic algorithm to search for higher-impact combinations.

3. Apply
   - `poison` applies reversible mutations to matched files.
   - `insert` adds context payloads as comments or sections.
   - `replace` performs targeted string replacements to soften or shift guidance.
   - All changes are backed up for reversal and auditing.

4. Simulate
   - `agent` runs an offline mock agent or a real LLM adapter.
   - Outputs are stored as artifacts for analysis.

5. Analyze
   - `analyze` scans agent output for signals and produces findings.
   - `report` renders findings to Markdown or JSON.

### Key modules

- `sneakyagent/scanner`: layer discovery and file selection.
- `sneakyagent/poison`: strategy planning and mutation application.
- `sneakyagent/agent`: offline and LLM-backed agent execution.
- `sneakyagent/analyze`: output inspection and findings.
- `sneakyagent/report`: report rendering.
- `sneakyagent/storage`: run manifests, backups, and artifacts.

### Mutation model

- Templates live in `sneakyagent/data/rules.yaml`.
- Each template specifies category, layer, target globs, and action.
- `insert` uses content payloads; `replace` uses pattern replacements.
- Intensity controls insertion length and replacement frequency.

### LLM integration points

- Agent simulation: `sneakyagent/agent/llm.py` defines `LLMAdapter`.
- Poison mutation: `sneakyagent/poison/llm.py` defines `PoisonLLMAdapter`.
- Both ship with no-op adapters that raise until configured.

### Run artifacts

- `manifest.json`: metadata, categories, intensity, and mutation list.
- `backup/`: original file snapshots for reversal.
- `artifacts/`: agent output and analysis reports.

### Limitations

- Interpretation: findings are signals, not verdicts. Results should be
  reviewed alongside diffs, run artifacts, and domain context.


