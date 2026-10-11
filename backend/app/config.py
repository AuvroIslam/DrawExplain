"""Runtime settings, loaded from the repo-root .env file."""
from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

BACKEND_DIR = Path(__file__).resolve().parents[1]
ROOT_DIR = BACKEND_DIR.parent
load_dotenv(ROOT_DIR / ".env")

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
# gpt-5.5 traces worked examples correctly (gpt-5.4-mini mis-traced Dijkstra) at similar latency.
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5.5")
OPENAI_REASONING_EFFORT = os.getenv("OPENAI_REASONING_EFFORT", "low")

ELEVENLABS_API_KEY = os.getenv("ELEVENLABS_API_KEY", "")
ELEVENLABS_VOICE_ID = os.getenv("ELEVENLABS_VOICE_ID", "Xb7hH8MSUJpSbSDYk0k2")  # "Alice - Clear, Engaging Educator"
ELEVENLABS_MODEL_ID = os.getenv("ELEVENLABS_MODEL_ID", "eleven_flash_v2_5")

DATA_DIR = Path(os.getenv("DATA_DIR", str(BACKEND_DIR / "data")))
SAMPLES_DIR = Path(os.getenv("SAMPLES_DIR", str(ROOT_DIR / "samples")))
MAX_IMAGE_SIDE = int(os.getenv("MAX_IMAGE_SIDE", "1600"))
LLM_CACHE = os.getenv("LLM_CACHE", "0") == "1"

# Optional GPU perception service (backend/gpu/modal_app.py on Modal): SAM 2.1 masks refine
# low-confidence drawing targets, formula OCR adds LaTeX to maths lines. On only when both are set.
GPU_URL = os.getenv("GPU_URL", "").strip().rstrip("/")
GPU_KEY = os.getenv("GPU_KEY", "").strip()
GPU_ENABLED = bool(GPU_URL and GPU_KEY) and os.getenv("GPU_ENABLED", "1").strip().lower() not in ("0", "false", "no", "off")
try:
    GPU_TIMEOUT = float(os.getenv("GPU_TIMEOUT", "20"))  # seconds per request
except ValueError:
    GPU_TIMEOUT = 20.0
GPU_SAM = os.getenv("GPU_SAM", "1") != "0"  # SAM refinement of llm_refined / llm_only / figure targets
GPU_LATEX = os.getenv("GPU_LATEX", "1") != "0"  # formula OCR during perception
GPU_WAIT_COLD = os.getenv("GPU_WAIT_COLD", "0") == "1"  # wait for a cold container instead of skipping it

DATA_DIR.mkdir(parents=True, exist_ok=True)
