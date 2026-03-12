# SneakyAgent 
<img src="docs/mascot.png" width="300" align="middle">
SneakyAgent is a red-teaming tool that evaluates how workspace context influences AI coding agents.
It scans a repository, injects reversible context signals, and analyzes the impact in a controlled way.

## What it does

SneakyAgent models how subtle changes to repository context can influence agent behavior.
It targets common context layers (AI instructions, docs, config, templates, tooling, code metadata),
applies reversible mutations, and records outputs for analysis.

The tool is designed for controlled evaluation and does not ship with exploit payloads or bypass logic.

## SneakyAgent Context Manipulation Pipeline

```mermaid
flowchart TD

A[Target Repository]

A --> B[Scanner<br/>Identify Context Layers<br/>docs / configs / templates / metadata]

B --> C[Mutation Engine]

C --> C1[Template-Based Mutations]
C --> C2[Search / GA-Based Mutations]

C1 --> D[Apply Context Changes]
C2 --> D

D --> E[Agent Execution<br/>Run Development Task<br/>through AI Coding Agent]

E --> F[Analyzer<br/>Detect Behavioral Shifts<br/>in Generated Code]

F --> G[Report<br/>Context → Behavior Influence Mapping]
```

## SneakyAgent Attack Path

```mermaid
flowchart TD

A[Attacker]

A --> B[Repository Influence<br/>PR / Commit / Dependency / Template Update]

B --> C[Context Manipulation Engine]

C --> C1[Template-Based Context Signals]
C --> C2[Search / GA-Based Context Mutations]

C1 --> D[Workspace Context Modified]
C2 --> D

D --> E[AI Coding Agent Reads Workspace Context]

E --> F[Agent Interprets Context as Guidance]

F --> G[Task Execution<br/>refactor / implement / modify code]

G --> H[Influenced Code Generation]

H --> H1[Weaker Validation]
H --> H2[Relaxed Security Controls]
H --> H3[Insecure Defaults]
H --> H4[Unsafe Code Patterns]

H1 --> I[Code Committed / Merged]
H2 --> I
H3 --> I
H4 --> I

I --> J[Security Impact Introduced]
```
## How it works

1. Scan: Enumerate context layers in the target repo.
2. Plan: Select mutation templates by category, intensity, and layer scope.
3. Apply: Insert or replace content in matched files, with backups for reversal.
4. Simulate: Run an offline or LLM-backed agent against a task prompt.
5. Analyze: Score and report on outputs for policy or security signals.

## Operational model

- Reversible: Mutations are tracked with before/after snapshots.
- Targeted: Templates use glob patterns to match files by layer.
- Scaled: Intensity levels control how much content is injected or replaced.
- Auditable: Each run persists a manifest and artifacts for review.

## Modules

- `scanner`: Detects context layers and collects candidate files.
- `poison`: Plans and applies reversible context mutations.
- `agent`: Runs offline or LLM-backed agent simulations.
- `analyze`: Scans outputs for policy or security indicators.
- `report`: Writes human-readable summaries of findings.
- `storage`: Persists runs, backups, and artifacts.

## Capabilities

- Context layer discovery across common repo surfaces.
- Template-driven insert and replacement mutations.
- Multiple strategies for mutation planning (heuristic, GA).
- Offline agent simulation for safe local testing.
- Optional LLM adapter for live agent evaluation.
- JSON and Markdown reporting for findings.
 
 ## Quick start
 
 ```bash
 pip install -e .
 sneakyagent scan /path/to/repo
 sneakyagent poison /path/to/repo --categories auth-weaken,validation-relax --intensity subtle
 sneakyagent test /path/to/repo --task "refactor auth module" --mode offline
 sneakyagent report /path/to/run-id --format md
 ```
 
 
