"""
MCP vs Direct vs CLI Benchmark

Usage: uv run python -m src.benchmark [--runs N] [--claude-model MODEL] [--openai-model MODEL] [--tasks TASK1,TASK2]
"""

import asyncio
import json
import os
import tempfile
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

import typer
from rich.console import Console
from rich.panel import Panel

from src.harness.claude_code_runner import run_claude_code_benchmark
from src.harness.reporter import format_results
from src.harness.runner import run_benchmark
from src.tasks.registry import get_task, list_tasks
from src.tools.cli.wrapper import CliToolProvider
from src.tools.direct.tools import DirectToolProvider
from src.tools.mcp.client import McpToolProvider

console = Console()

DEFAULT_CLAUDE_MODEL = "claude-sonnet-4-20250514"
DEFAULT_OPENAI_MODEL = "gpt-4o"


def _detect_llms(claude_model: str, openai_model: str) -> dict[str, tuple[str, str]]:
    """Detect available LLMs based on API keys. Returns {label: (llm_type, model)}."""
    llms = {}
    if os.environ.get("ANTHROPIC_API_KEY"):
        llms[f"Claude ({claude_model})"] = ("anthropic", claude_model)
    if os.environ.get("OPENAI_API_KEY"):
        llms[f"GPT ({openai_model})"] = ("openai", openai_model)
    return llms


def main(
    runs: int = typer.Option(3, help="Number of runs per approach"),
    claude_model: str = typer.Option(DEFAULT_CLAUDE_MODEL, help="Claude model to use"),
    openai_model: str = typer.Option(DEFAULT_OPENAI_MODEL, help="OpenAI model to use"),
    tasks: str = typer.Option(
        "",
        help="Comma-separated task names to run (default: all). Use --list-tasks to see available.",
    ),
    list_task_names: bool = typer.Option(
        False, "--list-tasks", help="List available tasks and exit"
    ),
):
    """Run the MCP vs Direct vs CLI benchmark."""
    if list_task_names:
        console.print("[bold]Available tasks:[/bold]")
        for name in list_tasks():
            task = get_task(name)
            console.print(f"  • {name}: {task.description}")
        raise typer.Exit(0)

    asyncio.run(_run(runs, claude_model, openai_model, tasks))


async def _run(runs: int, claude_model: str, openai_model: str, tasks_filter: str):
    llms = _detect_llms(claude_model, openai_model)

    if not llms:
        console.print(
            "[bold red]No API keys found.[/bold red]\n"
            "Set ANTHROPIC_API_KEY and/or OPENAI_API_KEY in your .env file."
        )
        raise typer.Exit(1)

    # Resolve which tasks to run
    if tasks_filter.strip():
        task_names = [t.strip() for t in tasks_filter.split(",") if t.strip()]
    else:
        task_names = list_tasks()

    task_instances = [get_task(name) for name in task_names]

    console.print(f"[bold]Detected LLMs:[/bold] {', '.join(llms.keys())}")
    console.print(f"[bold]Tasks:[/bold] {', '.join(task_names)}")
    console.print(f"[bold]Runs per approach:[/bold] {runs}\n")

    # Results structure:
    # {task_name: {agent_label: {approach_name: metrics}}}
    #
    # For custom runner agents (one per LLM):
    #   agent_label = "Custom Runner (Claude ...)" or "Custom Runner (GPT ...)"
    #   approach_name = "direct" / "cli" / "mcp (3 tools)" / "mcp (all tools)"
    #
    # For Claude Code agent:
    #   agent_label = "Claude Code"
    #   approach_name = "built-in" / "mcp"
    all_results = {}

    for task in task_instances:
        console.print(f"\n[bold yellow]{'━' * 60}[/bold yellow]")
        console.print(f"[bold yellow]Task: {task.name} — {task.description}[/bold yellow]")
        console.print(f"[bold yellow]{'━' * 60}[/bold yellow]")

        task_results = {}

        # --- Custom runner agents (one per LLM) ---
        for llm_label, (llm_type, model) in llms.items():
            agent_label = f"Custom Runner — {llm_label}"
            console.print(f"\n[bold magenta]  {agent_label}[/bold magenta]")

            with tempfile.TemporaryDirectory() as raw_tmp_dir:
                tmp_dir = str(Path(raw_tmp_dir).resolve())

                providers = {
                    "direct": DirectToolProvider(),
                    "cli": CliToolProvider(),
                    "mcp (3 tools)": McpToolProvider(allowed_dirs=[tmp_dir], filter_tools=True),
                    "mcp (all tools)": McpToolProvider(allowed_dirs=[tmp_dir], filter_tools=False),
                }

                approach_results = {}

                for prov_name, provider in providers.items():
                    console.print(f"    [bold blue]Running: {prov_name}[/bold blue]")
                    await provider.setup()
                    try:
                        task.setup(tmp_dir)
                        prompt = task.get_prompt(tmp_dir)

                        approach_results[prov_name] = await run_benchmark(
                            provider, prompt, model=model, llm=llm_type, runs=runs
                        )

                        valid = task.validate(tmp_dir)
                        approach_results[prov_name]["task_valid"] = valid
                        status = "[green]✓[/green]" if valid else "[red]✗[/red]"

                        console.print(
                            f"      {status} avg {approach_results[prov_name]['avg_total_time_s']:.1f}s"
                        )
                    finally:
                        await provider.teardown()

                task_results[agent_label] = approach_results

        # --- Claude Code agent (Anthropic only) ---
        anthropic_entries = [
            (label, model)
            for label, (llm_type, model) in llms.items()
            if llm_type == "anthropic"
        ]
        if anthropic_entries:
            llm_label, model = anthropic_entries[0]
            agent_label = f"Claude Code — {llm_label}"
            console.print(f"\n[bold magenta]  {agent_label}[/bold magenta]")

            cc_model = model
            if "sonnet" in model:
                cc_model = "sonnet"
            elif "opus" in model:
                cc_model = "opus"
            elif "haiku" in model:
                cc_model = "haiku"

            approach_results = {}

            for mode in ("built-in", "bash", "mcp (3 tools)", "mcp (all tools)"):
                console.print(f"    [bold blue]Running: {mode}[/bold blue]")

                with tempfile.TemporaryDirectory() as raw_tmp_dir:
                    tmp_dir = str(Path(raw_tmp_dir).resolve())
                    task.setup(tmp_dir)
                    prompt = task.get_prompt(tmp_dir)

                    approach_results[mode] = await run_claude_code_benchmark(
                        prompt=prompt,
                        work_dir=tmp_dir,
                        model=cc_model,
                        runs=runs,
                        setup_fn=task.setup,
                        mode=mode,
                    )

                    valid = task.validate(tmp_dir)
                    approach_results[mode]["task_valid"] = valid
                    status = "[green]✓[/green]" if valid else "[red]✗[/red]"

                    console.print(
                        f"      {status} avg {approach_results[mode]['avg_total_time_s']:.1f}s"
                    )

            task_results[agent_label] = approach_results

        all_results[task.name] = task_results

    # Format and display
    report = format_results(all_results)
    console.print(Panel(report, title="Benchmark Results", border_style="green"))

    results_dir = Path("results")
    results_dir.mkdir(exist_ok=True)
    timestamp = datetime.now().strftime("%Y-%m-%d-%H%M")

    filename = results_dir / f"benchmark-{timestamp}.md"
    filename.write_text(report)
    console.print(f"\nResults saved to [bold]{filename}[/bold]")

    # Save detailed traces
    trace_file = results_dir / f"traces-{timestamp}.json"
    trace_file.write_text(json.dumps(all_results, indent=2, default=str))
    console.print(f"Traces saved to [bold]{trace_file}[/bold]")


if __name__ == "__main__":
    typer.run(main)
