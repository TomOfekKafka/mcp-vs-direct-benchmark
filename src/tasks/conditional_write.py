import random
from pathlib import Path


class ConditionalWriteTask:
    """Read a file and only write summary.txt if status is active."""

    def __init__(self):
        self._status: str = "active"

    @property
    def name(self) -> str:
        return "conditional-write"

    @property
    def description(self) -> str:
        return "Read hello.txt, write summary.txt only if status is active"

    def setup(self, work_dir: str) -> None:
        self._status = random.choice(["active", "inactive"])
        hello = Path(work_dir) / "hello.txt"
        hello.write_text(f"status: {self._status}\nThis file tests conditional logic.")
        # Ensure no leftover summary from a previous run
        summary = Path(work_dir) / "summary.txt"
        if summary.exists():
            summary.unlink()

    def get_prompt(self, work_dir: str) -> str:
        return (
            f"Read the file called hello.txt in {work_dir}. "
            "If the status field is 'active', write a file called summary.txt "
            "containing a one-line summary of what you found. "
            "If the status is 'inactive', do NOT write summary.txt — just say that "
            "the status was inactive and no file was written."
        )

    def validate(self, work_dir: str) -> bool:
        summary = Path(work_dir) / "summary.txt"
        if self._status == "active":
            return summary.exists() and len(summary.read_text().strip()) > 0
        else:
            return not summary.exists()
