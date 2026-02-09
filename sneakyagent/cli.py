from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import List, Optional

import typer

from sneakyagent.agent.runner import AgentRunner
from sneakyagent.analyze.analyzer import SecurityAnalyzer
from sneakyagent.models import AgentTask, RunManifest
from sneakyagent.poison import (
    GeneticStrategy,
    HeuristicStrategy,
    OpenAIPoisonLLMAdapter,
    PatchApplier,
    RuleCatalog,
)
from sneakyagent.scanner import RepoScanner
from sneakyagent.storage.manifest import RunStore
from sneakyagent.utils import utc_now_iso

logger = logging.getLogger("sneakyagent")

app = typer.Typer(no_args_is_help=True)

BANNER = r"""
  ____                 _          _                    _
 / ___| _ __   ___  ___| |_ __ _  | |    _ __   ___  __| |
 \___ \| '_ \ / _ \/ __| __/ _` | | |   | '_ \ / _ \/ _` |
  ___) | | | |  __/ (__| || (_| | | |___| | | |  __/ (_| |
 |____/|_| |_|\___|\___|\__\__,_| |_____|_| |_|\___|\__,_|
"""

ALL_LAYERS = [
    "ai_instructions",
    "documentation",
    "configuration",
    "infrastructure",
    "templates",
    "tooling",
    "code_metadata",
]


@app.callback()
def _main(
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Enable verbose logging"),
) -> None:
    typer.echo(BANNER)
    level = logging.DEBUG if verbose else logging.WARNING
    logging.basicConfig(level=level, format="%(levelname)s: %(message)s")


def _parse_categories(categories: str) -> List[str]:
    if not categories:
        return []
    return [c.strip() for c in categories.split(",") if c.strip()]


def _parse_layers(layers: str) -> List[str]:
    """Parse comma-separated layer names. Returns empty list if none specified."""
    if not layers:
        return []
    parsed = [l.strip() for l in layers.split(",") if l.strip()]
    for layer in parsed:
        if layer not in ALL_LAYERS:
            typer.echo(f"Unknown layer: {layer}. Available: {', '.join(ALL_LAYERS)}")
            raise typer.Exit(code=1)
    return parsed


def _run_id() -> str:
    return utc_now_iso().replace(":", "").replace("-", "").split(".")[0]


def _allowed_layers(level: int, explicit_layers: List[str]) -> List[str]:
    """If explicit layers are given, use those. Otherwise use cumulative level."""
    if explicit_layers:
        return explicit_layers
    level = max(1, min(level, len(ALL_LAYERS)))
    return ALL_LAYERS[:level]


@app.command()
def scan(repo: Path) -> None:
    """Scan repository for context layers."""
    scanner = RepoScanner()
    result = scanner.scan(repo)
    payload = {k: [str(p) for p in v] for k, v in result.layers.items()}
    for layer, files in payload.items():
        logger.info("Layer %s: %d files", layer, len(files))
    typer.echo(json.dumps(payload, indent=2))


@app.command(name="list-templates")
def list_templates(
    categories: str = typer.Option("", help="Filter by categories (comma-separated)"),
    layer: str = typer.Option("", help="Filter by layer name"),
) -> None:
    """List available mutation templates."""
    catalog = RuleCatalog.load_default()
    category_list = _parse_categories(categories)
    templates = catalog.by_category(category_list)
    if layer:
        templates = [t for t in templates if t.layer == layer]

    if not templates:
        typer.echo("No templates found matching the criteria.")
        return

    # Group by category
    by_cat: dict[str, list] = {}
    for t in templates:
        by_cat.setdefault(t.category, []).append(t)

    for cat, tmpls in sorted(by_cat.items()):
        typer.echo(f"\n[{cat}] ({len(tmpls)} templates)")
        for t in tmpls:
            action_info = f"action={t.action}"
            if t.action == "replace" and t.replacements:
                pairs = ", ".join(f'"{r.pattern}"→"{r.replacement}"' for r in t.replacements[:3])
                action_info = f"replace: {pairs}"
            globs = ", ".join(t.target_globs[:4])
            if len(t.target_globs) > 4:
                globs += f" (+{len(t.target_globs) - 4} more)"
            typer.echo(f"  {t.id}")
            typer.echo(f"    layer: {t.layer} | {action_info}")
            typer.echo(f"    targets: {globs}")

    typer.echo(f"\nTotal: {len(templates)} templates")


@app.command()
def poison(
    repo: Path,
    categories: str = typer.Option("", help="Comma-separated categories (empty = all)"),
    intensity: str = typer.Option("subtle", help="subtle|normal|strong"),
    strategy: str = typer.Option("heuristic", help="heuristic|ga"),
    use_llm: bool = typer.Option(
        False, "--use-llm/--no-use-llm", help="Use LLM-generated mutation content"
    ),
    llm_model: str = typer.Option("gpt-4o-mini", help="Model for LLM-generated content"),
    layer_level: int = typer.Option(
        3,
        help=(
            "1=AI instructions, 2=+docs, 3=+config, 4=+infra, "
            "5=+templates, 6=+tooling, 7=+code metadata"
        ),
    ),
    layers: str = typer.Option(
        "",
        help="Explicit comma-separated layers (overrides --layer-level)",
    ),
) -> None:
    """Apply reversible context mutations."""
    scanner = RepoScanner()
    result = scanner.scan(repo)
    catalog = RuleCatalog.load_default()

    category_list = _parse_categories(categories)
    explicit_layers = _parse_layers(layers)
    allowed_layers = _allowed_layers(layer_level, explicit_layers)

    if not category_list:
        logger.info("No categories specified, using all %d templates", len(catalog.templates))
    else:
        logger.info("Categories: %s", ", ".join(category_list))
    logger.info("Allowed layers: %s", ", ".join(allowed_layers))

    if strategy == "ga":
        planner = GeneticStrategy()
    else:
        planner = HeuristicStrategy()

    plans = planner.plan(result, catalog, category_list, intensity, allowed_layers)
    logger.info("Planned %d mutations", len(plans))

    llm_adapter = None
    if use_llm:
        llm_adapter = OpenAIPoisonLLMAdapter(model=llm_model)

    applier = PatchApplier(llm_adapter=llm_adapter)
    mutations = applier.apply(plans, use_llm=use_llm)

    run_id = _run_id()
    store = RunStore(repo, run_id)
    manifest = RunManifest(
        run_id=run_id,
        repo_path=repo.resolve(),
        created_at=utc_now_iso(),
        strategy=strategy,
        categories=category_list,
        intensity=intensity,
        layer_level=layer_level,
        mutations=mutations,
        meta={"poison_llm": use_llm, "llm_model": llm_model if use_llm else None},
    )
    store.save_backups(mutations)
    store.save_manifest(manifest)

    typer.echo(f"run_id: {run_id}")
    typer.echo(f"mutations applied: {len(mutations)}")
    typer.echo(f"mutations skipped: {len(plans) - len(mutations)}")
    for m in mutations:
        rel = m.target_path.relative_to(repo.resolve()) if repo.resolve() in m.target_path.parents or repo.resolve() == m.target_path.parent else m.target_path.name
        logger.info("  mutated: %s (template=%s)", rel, m.template_id)


@app.command()
def test(
    repo: Path,
    task: str = typer.Option(..., help="Task for the agent"),
    mode: str = typer.Option("offline", help="offline|llm"),
    model: Optional[str] = typer.Option(None, help="Model name for LLM mode"),
    run_id: Optional[str] = typer.Option(None, help="Existing run id"),
    baseline_run_id: Optional[str] = typer.Option(
        None, help="Baseline run id for drift comparison"
    ),
) -> None:
    """Run agent simulation and analyze outputs."""
    if mode == "llm":
        from sneakyagent.agent.llm import OpenAIAgentAdapter

        llm_adapter = OpenAIAgentAdapter(model=model or "gpt-4o-mini")
        runner = AgentRunner(llm_adapter=llm_adapter)
    else:
        runner = AgentRunner()

    analyzer = SecurityAnalyzer()

    run_id = run_id or _run_id()
    store = RunStore(repo, run_id)
    agent_task = AgentTask(task=task, mode=mode, model=model)
    output = runner.run(repo, agent_task)

    store.save_artifact("agent_output.txt", output.content)
    findings = analyzer.analyze_text(output.content)
    diff_findings = []
    if baseline_run_id:
        baseline_store = RunStore(repo, baseline_run_id)
        baseline_path = baseline_store.artifacts_dir / "agent_output.txt"
        if not baseline_path.exists():
            typer.echo(f"baseline agent_output.txt not found for run {baseline_run_id}")
            raise typer.Exit(code=1)
        baseline_content = baseline_path.read_text(encoding="utf-8")
        diff_text = analyzer.build_diff(baseline_content, output.content)
        store.save_artifact("output_diff.txt", diff_text)
        diff_findings = analyzer.analyze_diff(baseline_content, output.content)

    report_data = {
        "run_id": run_id,
        "findings": [f.__dict__ for f in findings],
        "baseline_run_id": baseline_run_id,
        "diff_findings": [f.__dict__ for f in diff_findings],
    }
    store.save_artifact("analysis.json", json.dumps(report_data, indent=2))

    from sneakyagent.report.writer import ReportWriter

    writer = ReportWriter()
    markdown = writer.to_markdown(findings, diff_findings)
    store.save_artifact("analysis.md", markdown)

    typer.echo(f"run_id: {run_id}")
    typer.echo(f"findings: {len(findings)}")
    if diff_findings:
        typer.echo(f"drift findings: {len(diff_findings)}")


@app.command()
def report(repo: Path, run_id: str, format: str = "md") -> None:
    """Render report from a previous run."""
    store = RunStore(repo, run_id)
    data = store.load_manifest() if (store.base_dir / "manifest.json").exists() else {}
    analysis_path = store.artifacts_dir / "analysis.json"
    if not analysis_path.exists():
        typer.echo("analysis.json not found")
        raise typer.Exit(code=1)

    raw = json.loads(analysis_path.read_text(encoding="utf-8"))
    findings = raw.get("findings", [])
    diff_findings = raw.get("diff_findings", [])

    if format == "json":
        typer.echo(json.dumps({"findings": findings, "diff_findings": diff_findings}, indent=2))
        return
    if format == "md":
        lines = ["# SneakyAgent Report", ""]
        if data:
            lines.append(f"**Run:** {run_id}")
            lines.append(f"**Strategy:** {data.get('strategy', 'N/A')}")
            lines.append(f"**Intensity:** {data.get('intensity', 'N/A')}")
            lines.append(f"**Mutations:** {len(data.get('mutations', []))}")
            lines.append("")

        if findings:
            lines.append("## Findings")
            lines.append("")
            # Group by severity
            by_sev: dict[str, list] = {}
            for f in findings:
                by_sev.setdefault(f["severity"], []).append(f)
            for sev in ["high", "medium", "low"]:
                items = by_sev.get(sev, [])
                if items:
                    lines.append(f"### {sev.upper()} ({len(items)})")
                    for f in items:
                        lines.append(f"- **{f['rule_id']}**: {f['snippet']}")
                    lines.append("")
        else:
            lines.append("## Findings\n\nNo findings.\n")

        if diff_findings:
            lines.append("## Drift Findings")
            lines.append("")
            for f in diff_findings:
                lines.append(f"- **{f['rule_id']}** ({f['severity']}): {f['snippet']}")
            lines.append("")

        typer.echo("\n".join(lines))
        return
    typer.echo("format must be md or json")
    raise typer.Exit(code=1)
