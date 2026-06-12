from __future__ import annotations

import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent

try:
    from dotenv import load_dotenv

    load_dotenv(PROJECT_ROOT / ".env")
except ImportError:
    pass

DATA_DIR = PROJECT_ROOT / "data"
DB_PATH = Path(os.getenv("EDH_BUILDER_DB", PROJECT_ROOT / "edh_builder.sqlite3"))
SCRYFALL_BULK_URL = "https://api.scryfall.com/bulk-data/oracle-cards"

LLM_PROVIDER = os.getenv("LLM_PROVIDER", os.getenv("OPENAI_PROVIDER", "openai"))
LLM_API_KEY = os.getenv("LLM_API_KEY", os.getenv("OPENAI_API_KEY", ""))
LLM_BASE_URL = os.getenv("LLM_BASE_URL", os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")).rstrip("/")
LLM_MODEL = os.getenv("LLM_MODEL", os.getenv("OPENAI_MODEL", "gpt-4.1-mini"))

# Backward-compatible aliases for older code and existing .env files.
OPENAI_API_KEY = LLM_API_KEY
OPENAI_BASE_URL = LLM_BASE_URL
OPENAI_MODEL = LLM_MODEL
