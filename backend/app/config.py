"""Runtime settings, loaded from the repo-root .env file."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[1]
ROOT_DIR = BACKEND_DIR.parent
load_dotenv(ROOT_DIR / ".env")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
# gpt-5.4-mini: ~2s and 0.95 mean IoU on raw boxes in our probe; gpt-5.5 is slower but strongest.
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.4-mini")
OPENAI_REASONING_EFFORT = os.getenv("OPENAI_REASONING_EFFORT", "low")

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "Xb7hH8MSUJpSbSDYk0k2")  # "Alice - Clear, Engaging Educator"
ELEVENLABS_MODEL_ID = os.getenv("ELEVENLABS_MODEL_ID", "eleven_flash_v2_5")

DATA_DIR = Path(os.getenv("DATA_DIR", str(BACKEND_DIR / "data")))
SAMPLES_DIR = Path(os.getenv("SAMPLES_DIR", str(ROOT_DIR / "samples")))
MAX_IMAGE_SIDE = int(os.getenv("MAX_IMAGE_SIDE", "1600"))
LLM_CACHE = os.getenv("LLM_CACHE", "0") == "1"

DATA_DIR.mkdir(parents=True, exist_ok=True)
