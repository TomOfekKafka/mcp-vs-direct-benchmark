from pathlib import Path


class FileOpsTask:
    """The original benchmark task: list, read, then summarize into a new file."""

    @property
    def name(self) -> str:
        return "file-ops"

    @property
    def description(self) -> str:
        return "List files, read hello.txt, write a one-line summary to summary.txt"

    def setup(self, work_dir: str) -> None:
        hello = Path(work_dir) / "hello.txt"
        hello.write_text("Hello from the benchmark! This file tests read operations.")

    def get_prompt(self, work_dir: str) -> str:
        return (
            f"List the files in {work_dir}, read the file called hello.txt, "
            "then write a file called summary.txt containing a one-line summary of what you found."
        )

    def validate(self, work_dir: str) -> bool:
        summary = Path(work_dir) / "summary.txt"
        return summary.exists() and len(summary.read_text().strip()) > 0
