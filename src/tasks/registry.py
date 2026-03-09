from src.tasks.conditional_write import ConditionalWriteTask
from src.tasks.file_ops import FileOpsTask

TASKS = {
    "file-ops": FileOpsTask,
    "conditional-write": ConditionalWriteTask,
}


def get_task(name: str):
    """Get a task instance by name."""
    if name not in TASKS:
        available = ", ".join(TASKS.keys())
        raise ValueError(f"Unknown task: {name!r}. Available: {available}")
    return TASKS[name]()


def list_tasks() -> list[str]:
    """Return all registered task names."""
    return list(TASKS.keys())
