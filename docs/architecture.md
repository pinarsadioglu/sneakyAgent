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

- Analysis depth: the current analyzer is regex-based and limited by
  `sneakyagent/data/patterns.yaml`, so it can detect risky language but
  cannot prove that security was actually weakened.
- Coverage: only patterns that are explicitly defined are detected; new
  or indirect degradations can be missed.
- Interpretation: findings are signals, not verdicts. Results should be
  reviewed alongside diffs, run artifacts, and domain context.

### Reducing analysis limitations

The most reliable way to quantify impact is to compare poisoned vs baseline
outputs and interpret drift with a hybrid pipeline.

1. Baseline vs poisoned diff
   - Run the same task twice (no poison vs poison).
   - Compare generated outputs and changed files to detect drift.

2. Rule-based prefilter
   - Use deterministic rules (Semgrep/CodeQL or custom diff heuristics).
   - Catch clear regressions: auth checks removed, validation bypass,
     dangerous APIs, weakened crypto, blanket error swallowing.

3. LLM triage (structured)
   - Use LLMs as a reviewer, not a judge.
   - Ask for structured output: risk category, claim, evidence lines,
     confidence, and proposed tests/invariants.

4. Invariant and test validation
   - Encode security invariants as tests or assertions.
   - Run the same tests on baseline and poisoned outputs.
   - Drift is confirmed only when tests pass on baseline and fail on poison.
