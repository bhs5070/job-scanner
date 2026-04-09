from functools import lru_cache
from pathlib import Path

PROMPTS_DIR = Path(__file__).parent


@lru_cache(maxsize=None)
def load_prompt(name: str) -> str:
    """Load a prompt template by name.

    Args:
        name: Prompt file name without extension (e.g., "router").
              Must contain only alphanumeric characters and underscores.

    Returns:
        The prompt text content.

    Raises:
        ValueError: If the name contains invalid characters or resolves outside PROMPTS_DIR.
        FileNotFoundError: If the prompt file does not exist.
    """
    if not name or not all(c.isalnum() or c == "_" for c in name):
        raise ValueError(f"Invalid prompt name: {name!r}")

    resolved = (PROMPTS_DIR / f"{name}.txt").resolve()

    # Path traversal guard: ensure the resolved path stays within PROMPTS_DIR
    try:
        resolved.relative_to(PROMPTS_DIR.resolve())
    except ValueError:
        raise ValueError(f"Prompt name resolves outside prompts directory: {name!r}")

    if not resolved.exists():
        raise FileNotFoundError(f"Prompt file not found: {resolved}")

    return resolved.read_text(encoding="utf-8").strip()
