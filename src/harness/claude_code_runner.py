"""Runner that uses the Claude Code CLI as the agent."""

import asyncio
import json
import os
import tempfile
import time


def _avg(values: list) -> float:
    return sum(values) / len(values) if values else 0


async def run_claude_code_benchmark(
    prompt: str,
    work_dir: str,
    model: str = "sonnet",
    runs: int = 3,
    setup_fn=None,
    timeout_s: int = 120,
    mode: str = "built-in",
) -> dict:
    """Run a benchmark using Claude Code CLI.

    Args:
        prompt: The task prompt.
        work_dir: Working directory for the task.
        model: Claude Code model alias (e.g. "sonnet", "opus", "haiku").
        runs: Number of runs.
        setup_fn: Optional callable(work_dir) to reset task state before each run.
        timeout_s: Timeout per run in seconds (default 120).
        mode: "built-in" (native Claude Code tools),
              "bash" (only Bash tool for file operations),
              "mcp (3 tools)" (MCP server, filtered to 3 tools),
              or "mcp (all tools)" (MCP server, all tools exposed).
    """
    all_total_times = []
    all_input_tokens = []
    all_output_tokens = []
    all_traces = []

    for run_idx in range(runs):
        print(f"        claude-code ({mode}) run {run_idx + 1}/{runs}...", end="", flush=True)
        if setup_fn:
            setup_fn(work_dir)

        start_time = time.perf_counter()

        # Build env without CLAUDECODE to avoid nested-session block
        env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}

        cmd = [
            "claude",
            "-p", prompt,
            "--output-format", "json",
            "--no-session-persistence",
            "--model", model,
            "--permission-mode", "bypassPermissions",
            "--add-dir", work_dir,
        ]

        mcp_config_file = None

        if mode == "bash":
            # Only allow Bash — force shell commands for file operations
            cmd.extend([
                "--allowedTools", "Bash",
            ])
            cmd.extend([
                "--append-system-prompt",
                "You MUST use the Bash tool for all file operations (cat, ls, "
                "echo, etc.). Do not use any other tools.",
            ])

        elif mode in ("mcp (3 tools)", "mcp (all tools)"):
            # Write a temporary MCP config pointing to the filesystem server
            mcp_config = {
                "mcpServers": {
                    "filesystem": {
                        "command": "npx",
                        "args": [
                            "-y",
                            "@modelcontextprotocol/server-filesystem",
                            work_dir,
                        ],
                    }
                }
            }
            mcp_config_file = tempfile.NamedTemporaryFile(
                mode="w", suffix=".json", delete=False
            )
            json.dump(mcp_config, mcp_config_file)
            mcp_config_file.close()

            cmd.extend(["--mcp-config", mcp_config_file.name])
            # Disable built-in file tools so Claude Code must use MCP
            cmd.extend([
                "--disallowedTools", "Read", "Edit", "Write", "Glob", "Grep",
            ])

            if mode == "mcp (3 tools)":
                # Only allow the 3 tools that match direct/CLI
                cmd.extend([
                    "--allowedTools",
                    "mcp__filesystem__read_file",
                    "mcp__filesystem__write_file",
                    "mcp__filesystem__list_directory",
                    "Bash",
                ])

            cmd.extend([
                "--append-system-prompt",
                "You MUST use the MCP filesystem tools (read_file, write_file, "
                "list_directory, etc.) for all file operations. Do not use Bash "
                "for file reading or writing.",
            ])

        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=work_dir,
            env=env,
        )

        try:
            stdout, stderr = await asyncio.wait_for(
                proc.communicate(), timeout=timeout_s
            )
        except asyncio.TimeoutError:
            proc.kill()
            await proc.communicate()
            total_time = time.perf_counter() - start_time
            all_total_times.append(total_time)
            all_input_tokens.append(0)
            all_output_tokens.append(0)
            all_traces.append({"error": f"Timed out after {timeout_s}s"})
            print(f" TIMEOUT ({timeout_s}s)", flush=True)
            continue
        finally:
            if mcp_config_file:
                os.unlink(mcp_config_file.name)

        total_time = time.perf_counter() - start_time
        print(f" {total_time:.1f}s", flush=True)

        trace = {
            "exit_code": proc.returncode,
            "stderr_preview": stderr.decode(errors="replace")[:500] if stderr else "",
        }

        # Parse JSON output for token metrics
        input_tokens = 0
        output_tokens = 0
        if stdout:
            try:
                result = json.loads(stdout.decode())
                trace["result_preview"] = str(result.get("result", ""))[:500]
                trace["num_turns"] = result.get("num_turns", 0)
                trace["session_id"] = result.get("session_id", "")

                usage = result.get("usage", {})
                input_tokens = usage.get("input_tokens", 0)
                output_tokens = usage.get("output_tokens", 0)

                trace["usage"] = usage
                trace["cost_usd"] = result.get("cost_usd", 0)
                trace["duration_ms"] = result.get("duration_ms", 0)
                trace["duration_api_ms"] = result.get("duration_api_ms", 0)
            except json.JSONDecodeError:
                trace["raw_stdout"] = stdout.decode(errors="replace")[:500]

        all_total_times.append(total_time)
        all_input_tokens.append(input_tokens)
        all_output_tokens.append(output_tokens)
        all_traces.append(trace)

    return {
        "tool_definition_tokens": 0,
        "avg_call_latency_ms": 0,
        "avg_total_time_s": _avg(all_total_times),
        "avg_api_input_tokens": _avg(all_input_tokens),
        "avg_cached_input_tokens": 0,
        "avg_api_output_tokens": _avg(all_output_tokens),
        "avg_api_turns": _avg([t.get("num_turns", 0) for t in all_traces]),
        "avg_tool_calls": 0,
        "traces": all_traces,
    }
