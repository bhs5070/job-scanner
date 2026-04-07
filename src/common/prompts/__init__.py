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
    """
    if not all(c.isalnum() or c == "_" for c in name):
        raise ValueError(f"Invalid prompt name: {name}")

    path = PROMPTS_DIR / f"{name}.txt"
    resolved = path.resolve()
    resolved.relative_to(PROMPTS_DIR.resolve())  # Raises ValueError if outside

    if not resolved.exists():
        raise FileNotFoundError(f"Prompt file not found: {path}")
    return resolved.read_text(encoding="utf-8").strip()
