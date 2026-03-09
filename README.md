# MCP vs Direct vs CLI Benchmark

**Benchmarking tool-wiring approaches across two agents — a custom API loop and Claude Code — so you can pick the right one.**

## The Question

When building AI agents, how should tools be connected to the LLM? MCP (Model Context Protocol) is the emerging standard for tool integration, but it introduces protocol overhead: server lifecycle, JSON-RPC serialization, and dynamic discovery. Is that overhead worth it when your tools run in the same process? And does the choice of agent matter?

This benchmark measures the concrete cost of each approach across latency, token usage, and end-to-end task completion — using both a custom API tool-call loop and Claude Code as the agent.

## Two Agents

### Custom Runner (API tool-call loop)

A minimal agent that calls the Anthropic/OpenAI API directly in a while-loop, executing tool calls and feeding results back. Supports four tool-wiring approaches:

- **Direct (Pydantic)** — In-process Python functions with Pydantic models. Zero serialization overhead, zero process boundaries.
- **CLI (subprocess)** — Standalone Python scripts invoked via `asyncio.create_subprocess_exec`. The agent shells out for every call.
- **MCP (3 tools)** — MCP filesystem server via stdio, filtered to 3 tools matching direct/CLI for a fair comparison.
- **MCP (all 14 tools)** — MCP filesystem server with all tools exposed, showing real-world schema overhead.

### Claude Code (CLI agent)

Claude Code invoked via `claude -p` in non-interactive mode. A full-featured agent with its own tool management. Tested with four approaches:

- **Built-in tools** — Native Claude Code tools (Read, Write, Bash, etc.). The zero-overhead baseline.
- **Bash only** — Only the Bash tool allowed. Shell commands for all file operations.
- **MCP (3 tools)** — MCP filesystem server, filtered to 3 tools, built-in file tools disabled.
- **MCP (all 14 tools)** — MCP filesystem server with all tools, built-in file tools disabled.

## Tasks

| Task | Description |
|------|-------------|
| **file-ops** | List files, read hello.txt, write a one-line summary to summary.txt |
| **conditional-write** | Read hello.txt, write summary.txt only if status is "active" (tests branching logic) |

```bash
uv run python -m src.benchmark --list-tasks   # see available tasks
uv run python -m src.benchmark --tasks file-ops  # run specific task(s)
```

## What We Measure

| Metric | Description |
|--------|-------------|
| **Token overhead** | Size of tool definitions sent in each API request |
| **Per-call latency** | Wall-clock time from tool invocation to result |
| **End-to-end task time** | Total time to complete a multi-step agent task |
| **Total API tokens** | Input + output tokens consumed across the full task |

## Run It Yourself

### Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/) package manager
- Node.js (required by MCP server runtime)
- Anthropic API key and/or OpenAI API key
- Claude Code CLI (for Claude Code agent benchmarks)

### Setup

```bash
git clone https://github.com/TomOfekKafka/mcp-vs-direct-benchmark.git
cd mcp-vs-direct-benchmark

cp .env.example .env
# Add ANTHROPIC_API_KEY and/or OPENAI_API_KEY to .env

uv sync --group dev
```

### Run

```bash
uv run python -m src.benchmark           # default: 3 runs per approach
uv run python -m src.benchmark --runs 2  # faster: 2 runs
```

The benchmark auto-detects which API keys are present and runs Claude, GPT, or both.

```bash
# Override models
uv run python -m src.benchmark --claude-model claude-sonnet-4-20250514 --openai-model gpt-4o-mini
```

Results are printed to the terminal and saved to `results/`.

## Results

Benchmark run on 2026-03-09, 2 runs per approach.

### Task: file-ops

#### Custom Runner — Claude (Sonnet 4)

| Metric | Direct (Pydantic) | CLI (subprocess) | MCP (3 tools) | MCP (all 14 tools) |
|--------|-------------------|-------------------|----------------|---------------------|
| Tool definition tokens | 203 | 186 | 461 | 2,044 |
| Avg tool call latency | 0.5 ms | 84.6 ms | 7.0 ms | 7.7 ms |
| Avg total task time | 13.1 s | 13.9 s | 13.3 s | 15.0 s |
| Avg API input tokens | 3,471 | 3,369 | 4,401 | 10,915 |
| Avg API output tokens | 486 | 484 | 507 | 499 |
| Avg API turns | 4 | 4 | 4 | 4 |
| Avg tool calls | 3 | 3 | 3 | 3 |

#### Custom Runner — GPT-4o

| Metric | Direct (Pydantic) | CLI (subprocess) | MCP (3 tools) | MCP (all 14 tools) |
|--------|-------------------|-------------------|----------------|---------------------|
| Tool definition tokens | 227 | 210 | 485 | 2,156 |
| Avg tool call latency | 1.2 ms | 96.5 ms | 11.5 ms | 13.2 ms |
| Avg total task time | 6.5 s | 4.2 s | 4.8 s | 5.2 s |
| Avg API input tokens | 1,225 | 1,184 | 1,899 | 5,348 |
| Avg API output tokens | 207 | 196 | 212 | 209 |
| Avg API turns | 4 | 4 | 4 | 4 |
| Avg tool calls | 3 | 3 | 3 | 3 |

#### Claude Code — Claude (Sonnet 4)

| Metric | Built-in tools | Bash only | MCP (3 tools) | MCP (all 14 tools) |
|--------|---------------|-----------|----------------|---------------------|
| Avg total task time | 17.6 s | 16.8 s | 14.2 s | 13.3 s |
| Avg API output tokens | 543 | 440 | 537 | 552 |
| Avg turns | 5 | 4 | 5 | 5 |

### Task: conditional-write

#### Custom Runner — Claude (Sonnet 4)

| Metric | Direct (Pydantic) | CLI (subprocess) | MCP (3 tools) | MCP (all 14 tools) |
|--------|-------------------|-------------------|----------------|---------------------|
| Tool definition tokens | 203 | 186 | 461 | 2,044 |
| Avg tool call latency | 0.4 ms | 95.5 ms | 6.2 ms | 13.0 ms |
| Avg total task time | 5.2 s | 4.6 s | 4.8 s | 8.5 s |
| Avg API input tokens | 1,486 | 1,438 | 1,942 | 8,096 |
| Avg API output tokens | 174 | 164 | 177 | 353 |
| Avg API turns | 2 | 2 | 2 | 3 |
| Avg tool calls | 1 | 1 | 1 | 2 |

#### Custom Runner — GPT-4o

| Metric | Direct (Pydantic) | CLI (subprocess) | MCP (3 tools) | MCP (all 14 tools) |
|--------|-------------------|-------------------|----------------|---------------------|
| Tool definition tokens | 227 | 210 | 485 | 2,156 |
| Avg tool call latency | 0.7 ms | 97.6 ms | 18.5 ms | 11.0 ms |
| Avg total task time | 3.0 s | 2.3 s | 5.0 s | 2.3 s |
| Avg API input tokens | 519 | 495 | 1,419 | 2,569 |
| Avg API output tokens | 65 | 66 | 146 | 72 |
| Avg API turns | 2 | 2 | 3 | 2 |
| Avg tool calls | 1 | 1 | 2 | 1 |

#### Claude Code — Claude (Sonnet 4)

| Metric | Built-in tools | Bash only | MCP (3 tools) | MCP (all 14 tools) |
|--------|---------------|-----------|----------------|---------------------|
| Avg total task time | 9.2 s | 12.0 s | 12.3 s | 14.1 s |
| Avg API output tokens | 311 | 230 | 376 | 368 |
| Avg turns | 3 | 2.5 | 4 | 4 |

### Analysis

**Tool-wiring overhead (Custom Runner)**

- MCP (3 tools) adds ~2x more tool definition tokens than Direct (461 vs 203), but end-to-end task time is comparable — LLM response latency dominates.
- MCP (all 14 tools) is where overhead becomes significant: ~10x more tool definition tokens (2,044) and ~3x more input tokens per task, though caching helps on subsequent turns.
- CLI subprocess overhead (~85-100ms per call) is measurable but doesn't meaningfully impact end-to-end time for these small tasks.

**Claude Code agent**

- Built-in tools are fastest for Claude Code, especially on the conditional task (9.2s vs 12-14s for MCP).
- MCP adds overhead even for a sophisticated agent — the pattern holds across both agents.
- Claude Code takes more total time than the custom runner (~17s vs ~13s for file-ops), reflecting the overhead of a full-featured agent.

**Cross-LLM (Custom Runner)**

- GPT-4o completes tasks ~2-3x faster than Claude, using ~3x fewer input tokens and ~2x fewer output tokens for the same task with the same number of turns.
- Both models handle the conditional task correctly, reducing to 1 tool call and 2 turns when the status is inactive.

### Takeaway

**MCP vs Direct/CLI**: MCP adds token overhead from richer tool schemas but doesn't meaningfully impact end-to-end time with a small tool set. With all 14 tools exposed, the overhead compounds. Pick your integration approach based on architecture needs, not performance — unless you're exposing many tools.

**Agent choice matters**: Claude Code is slower than a minimal custom runner for simple tasks, but brings capabilities (code execution, reasoning) that matter for complex tasks.

## When to Use What

| Approach | Use when... | Avoid when... |
|----------|-------------|---------------|
| **MCP** | Tools cross process/machine boundaries; third-party tool providers; marketplace/plugin scenarios; you need dynamic tool discovery | Tools are local to the agent process and you control them all |
| **Direct** | Tools run in the same process as the agent; you control all tool implementations; latency and token cost matter | You need to expose tools to external consumers or support a plugin model |
| **CLI** | Wrapping existing scripts or binaries; tools need to be independently testable from the terminal; polyglot toolchains | High-frequency tool calls where subprocess overhead adds up |

## Project Structure

```
mcp-vs-direct-benchmark/
├── src/
│   ├── benchmark.py              # Main benchmark entry point
│   ├── __main__.py               # Module runner
│   ├── harness/
│   │   ├── runner.py             # Custom runner (API tool-call loop)
│   │   ├── claude_code_runner.py # Claude Code CLI runner
│   │   ├── reporter.py           # Results formatting and comparison
│   │   └── token_counter.py      # Token usage tracking
│   ├── tasks/
│   │   ├── base.py               # BenchmarkTask protocol
│   │   ├── file_ops.py           # file-ops task
│   │   ├── conditional_write.py  # conditional-write task
│   │   └── registry.py           # Task registry
│   └── tools/
│       ├── interface.py           # Common tool interface
│       ├── mcp/
│       │   └── client.py          # MCP client + server lifecycle
│       ├── direct/
│       │   └── tools.py           # Pydantic-based direct tools
│       └── cli/
│           ├── wrapper.py         # Subprocess wrapper for CLI tools
│           ├── list_dir.py        # Standalone list_directory script
│           ├── read_file.py       # Standalone read_file script
│           └── write_file.py      # Standalone write_file script
├── tests/
│   ├── test_mcp_tools.py
│   ├── test_direct_tools.py
│   ├── test_cli_tools.py
│   └── test_harness.py
├── docs/plans/                    # Design docs and implementation plan
├── pyproject.toml
└── .env.example
```

## License

MIT
