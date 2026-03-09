from datetime import datetime

PROVIDER_LABELS = {
    "direct": "Direct (Pydantic)",
    "cli": "CLI (subprocess)",
    "mcp": "MCP (stdio)",
    "mcp (3 tools)": "MCP (3 tools)",
    "mcp (all tools)": "MCP (all 14 tools)",
    "built-in": "Built-in tools",
    "bash": "Bash only",
}

METRICS = [
    ("Tool definition tokens", "tool_definition_tokens", ""),
    ("Avg tool call latency", "avg_call_latency_ms", "ms"),
    ("Avg total task time", "avg_total_time_s", "s"),
    ("Avg API input tokens", "avg_api_input_tokens", ""),
    ("  ↳ cached", "avg_cached_input_tokens", ""),
    ("Avg API output tokens", "avg_api_output_tokens", ""),
    ("Avg API turns", "avg_api_turns", ""),
    ("Avg tool calls", "avg_tool_calls", ""),
]


def format_results(results: dict) -> str:
    """Format benchmark results as markdown.

    Primary format: {task: {agent_label: {approach: metrics}}}
    Also supports legacy formats for backwards compatibility.
    """
    first_val = next(iter(results.values()))

    # Legacy flat: {provider: {tool_definition_tokens: ...}}
    if isinstance(first_val, dict) and "tool_definition_tokens" in first_val:
        return _format_single_table(results, "Benchmark Results")

    # Check nesting depth to detect format
    if isinstance(first_val, dict):
        second_val = next(iter(first_val.values()))

        # {task: {agent: {approach: metrics}}} — primary format
        if isinstance(second_val, dict):
            third_val = next(iter(second_val.values()))
            if isinstance(third_val, dict) and "tool_definition_tokens" in third_val:
                return _format_task_agent(results)

        # {llm: {provider: metrics}} — legacy multi-LLM
        if isinstance(second_val, dict) and "tool_definition_tokens" in second_val:
            return _format_multi_llm(results)

    return _format_task_agent(results)


def _format_task_agent(results: dict) -> str:
    """Format results grouped by task, then by agent.

    Each agent gets its own comparison table of approaches.
    """
    sections = []
    sections.append(f"# Benchmark Results — {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    for task_name, agents in results.items():
        sections.append("")
        sections.append(f"## Task: {task_name}")

        for agent_label, approach_results in agents.items():
            sections.append("")
            sections.append(f"### {agent_label}")
            sections.append("")
            sections.append(_format_table(approach_results))

    return "\n".join(sections)


def _format_multi_llm(results: dict) -> str:
    """Format results for multiple LLMs (legacy)."""
    sections = []
    sections.append(f"# Benchmark Results — {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    for llm_name, provider_results in results.items():
        sections.append("")
        sections.append(f"## {llm_name}")
        sections.append("")
        sections.append(_format_table(provider_results))

    return "\n".join(sections)


def _format_single_table(provider_results: dict, title: str) -> str:
    """Format a single table (legacy flat format)."""
    lines = [f"# {title} — {datetime.now().strftime('%Y-%m-%d %H:%M')}"]
    lines.append("")
    lines.append(_format_table(provider_results))
    return "\n".join(lines)


def _format_table(approach_results: dict) -> str:
    """Format a comparison table for approach results."""
    approaches = list(approach_results.keys())
    labels = [PROVIDER_LABELS.get(a, a) for a in approaches]

    header = "| Metric | " + " | ".join(labels) + " |"
    separator = "|--------" + "".join("|-" + "-" * max(len(l), 5) for l in labels) + "|"

    lines = [header, separator]

    for label, key, unit in METRICS:
        suffix = f" {unit}" if unit else ""
        values = []
        for a in approaches:
            val = approach_results[a].get(key, 0) or 0
            values.append(f"{val:.1f}{suffix}")
        lines.append(f"| {label} | " + " | ".join(values) + " |")

    return "\n".join(lines)
