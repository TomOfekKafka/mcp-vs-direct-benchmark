from typing import Protocol


class BenchmarkTask(Protocol):
    """A benchmark task that can be evaluated across tool providers."""

    @property
    def name(self) -> str:
        """Short identifier for the task (used in CLI and reports)."""
        ...

    @property
    def description(self) -> str:
        """Human-readable description of what the task tests."""
        ...

    def setup(self, work_dir: str) -> None:
        """Prepare any files/state needed in work_dir before running."""
        ...

    def get_prompt(self, work_dir: str) -> str:
        """Return the prompt to send to the LLM."""
        ...

    def validate(self, work_dir: str) -> bool:
        """Optional: check whether the task was completed correctly.
        Returns True if valid, False otherwise. Default: always True."""
        ...
