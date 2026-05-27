import os
from pathlib import Path


def get_db_path() -> Path:
    """Return the configured SQLite database path."""
    return Path(os.getenv("DB_PATH", "./db/gaokao.db"))


def get_data_dir() -> Path:
    """Return the configured data directory."""
    return Path(os.getenv("DATA_DIR", "./data"))


def ensure_dirs() -> None:
    """Ensure required local data directories exist."""
    db_path = get_db_path()
    data_dir = get_data_dir()

    db_path.parent.mkdir(parents=True, exist_ok=True)
    data_dir.mkdir(parents=True, exist_ok=True)
    (data_dir / "sample").mkdir(parents=True, exist_ok=True)
    (data_dir / "uploads").mkdir(parents=True, exist_ok=True)


def get_llm_provider() -> str:
    """Return the configured LLM provider name."""
    return os.getenv("LLM_PROVIDER", "none")


def is_llm_enabled() -> bool:
    """Return whether an LLM provider is configured."""
    return get_llm_provider().lower() != "none"
