"""DrawExplain GPU perception service on Modal: SAM 2.1 box-prompted masks + formula OCR (Qwen2-VL-2B).

The language model plans, deterministic code computes; this service only sharpens what the CPU
pipeline already found. It is optional: the API calls it through app/perception/gpu.py and behaves
exactly as before whenever the service is unset, cold, slow or failing.

Deploy (from backend/; weights are baked into the image, so a cold start only loads them):
    .venv/Scripts/python -m modal secret create drawexplain-gpu GPU_KEY=<random>   (once)
    .venv/Scripts/python -m modal deploy gpu/modal_app.py

Every request needs the header X-DrawExplain-Key = GPU_KEY (constant-time compare).
    GET  /health                                  -> {ok, gpu, models, errors, uptime}
    POST /segment {image: b64 PNG/JPEG, boxes: [[x0, y0, x1, y1], ...] px}
                  -> {results: [{box, score, area, polygon} | null per box], width, height, timings}
    POST /latex   {crops: [b64 PNG, ...]}         -> {latex: [str | null per crop], timings}

Formula OCR: pix2tex (LaTeX-OCR) was tried first and misread 2 of the 4 kinematics formulas of
samples/synthetic/clean/formulas_kinematics.png (sans-serif italic slide fonts); Qwen2-VL-2B-Instruct
(Apache-2.0) read all of them and the fixture formulas exactly, ~1.4 s for a batch of 7 lines on a T4.
"""
# no "from __future__ import annotations": FastAPI must see the request models defined inside create_app()

import modal

APP_NAME = "drawexplain-gpu"
SECRET_NAME = "drawexplain-gpu"
MODEL_DIR = "/models"
SAM_FILE = "sam2.1_b.pt"  # SAM 2.1 base+ (ultralytics packaging), ~160 MB
VLM_REPO = "Qwen/Qwen2-VL-2B-Instruct"
VLM_DIR = f"{MODEL_DIR}/qwen2-vl-2b"
MAX_BOXES = 64
MAX_CROPS = 16
MAX_SIDE = 2400  # images are downscaled to this before segmentation (the API sends <= 1600 px)
LINE_HEIGHT = 64  # formula line crops are rescaled to this height (read best in our tests)
LATEX_PROMPT = ("Transcribe the mathematical expression in this image as LaTeX. "
                "Reply with the LaTeX only (no $ signs, no words).")


def _download_weights() -> None:
    """Runs once at image build time, so containers start with the weights on disk."""
    import os

    from huggingface_hub import snapshot_download

    os.makedirs(MODEL_DIR, exist_ok=True)
    os.chdir(MODEL_DIR)
    from ultralytics import SAM

    SAM(SAM_FILE)  # downloads into the working directory
    snapshot_download(VLM_REPO, local_dir=VLM_DIR,
                      allow_patterns=["*.json", "*.safetensors", "*.txt", "*.model", "*.tiktoken"])


image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("libgl1", "libglib2.0-0")
    .pip_install("torch==2.5.1", "torchvision==0.20.1")
    .pip_install(
        "ultralytics==8.3.150",
        "transformers==4.49.0",
        "accelerate==1.4.0",
        "fastapi[standard]==0.115.12",
    )
    .run_function(_download_weights)
    .env({"YOLO_OFFLINE": "1", "YOLO_VERBOSE": "False", "HF_HUB_OFFLINE": "1", "TOKENIZERS_PARALLELISM": "false"})
)

app = modal.App(APP_NAME, image=image)


# ---------------------------------------------------------------- models (inside the container)

class _Models:
    """Loads SAM, then the formula VLM, once per container in the background; serialises GPU use."""

    def __init__(self) -> None:
        import threading

        self.sam = None
        self.vlm = None
        self.proc = None
        self.errors: dict[str, str] = {}
        self.load_seconds: dict[str, float] = {}
        self.sam_ready = threading.Event()
        self.vlm_ready = threading.Event()
        self.gpu = threading.Lock()

    def load_all(self) -> None:
        import os
        import time
        import traceback

        t = time.perf_counter()
        try:
            from ultralytics import SAM

            self.sam = SAM(os.path.join(MODEL_DIR, SAM_FILE))
        except Exception:  # reported by /health and the endpoints
            self.errors["sam"] = traceback.format_exc(limit=3)
        finally:
            self.load_seconds["sam"] = round(time.perf_counter() - t, 2)
            self.sam_ready.set()
        t = time.perf_counter()
        try:
            import torch
            from transformers import AutoProcessor, Qwen2VLForConditionalGeneration

            self.vlm = Qwen2VLForConditionalGeneration.from_pretrained(
                VLM_DIR, torch_dtype=torch.float16, device_map="cuda")  # T4: no bf16; fp16 reads formulas fine
            self.proc = AutoProcessor.from_pretrained(VLM_DIR)
            self.proc.tokenizer.padding_side = "left"
        except Exception:
            self.errors["latex"] = traceback.format_exc(limit=3)
        finally:
            self.load_seconds["latex"] = round(time.perf_counter() - t, 2)
            self.vlm_ready.set()


def _mask_geometry(mask, max_points: int = 48) -> dict | None:
    """Tight box (ignoring specks) and a simplified outline polygon of one boolean mask."""
    import cv2
    import numpy as np

    m = np.ascontiguousarray(mask.astype(np.uint8))
    total = int(m.sum())
    if total == 0:
        return None
    n, labels, stats, _ = cv2.connectedComponentsWithStats(m, connectivity=8)
    keep = [k for k in range(1, n) if stats[k, cv2.CC_STAT_AREA] >= max(16, 0.02 * total)]
    if not keep:
        keep = [int(np.argmax(stats[1:, cv2.CC_STAT_AREA])) + 1]
    x0 = min(int(stats[k, cv2.CC_STAT_LEFT]) for k in keep)
    y0 = min(int(stats[k, cv2.CC_STAT_TOP]) for k in keep)
    x1 = max(int(stats[k, cv2.CC_STAT_LEFT] + stats[k, cv2.CC_STAT_WIDTH]) for k in keep)
    y1 = max(int(stats[k, cv2.CC_STAT_TOP] + stats[k, cv2.CC_STAT_HEIGHT]) for k in keep)
    main = int(max(keep, key=lambda k: stats[k, cv2.CC_STAT_AREA]))
    contours, _ = cv2.findContours((labels == main).astype(np.uint8), cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    polygon: list[list[int]] = []
    if contours:
        c = max(contours, key=cv2.contourArea)
        eps = 0.004 * cv2.arcLength(c, True)
        approx = cv2.approxPolyDP(c, eps, True)
        while len(approx) > max_points and eps < 1e4:
            eps *= 1.5
            approx = cv2.approxPolyDP(c, eps, True)
        polygon = [[int(p[0][0]), int(p[0][1])] for p in approx]
    return {"box": [x0, y0, x1, y1], "area": int(sum(int(stats[k, cv2.CC_STAT_AREA]) for k in keep)),
            "polygon": polygon}


def clean_latex(text: str) -> str | None:
    """Model output -> bare LaTeX: no $ / \\[ \\] delimiters or equation environments, compact spacing."""
    import re

    s = (text or "").strip()
    s = re.sub(r"\\begin\{(equation|align|displaymath|gather)\*?\}|\\end\{(equation|align|displaymath|gather)\*?\}",
               " ", s)
    for a, b in (("$$", "$$"), ("\\[", "\\]"), ("\\(", "\\)"), ("$", "$")):
        if s.startswith(a) and s.endswith(b) and len(s) > len(a) + len(b):
            s = s[len(a):len(s) - len(b)].strip()
    s = re.sub(r"(\\[A-Za-z]+)\s+(?=[A-Za-z])", "\\1\x00", s)  # keep the space that ends a command name
    s = re.sub(r"\s+", "", s).replace("\x00", " ")
    s = re.sub(r"\^\{(\w)\}", r"^\1", s)
    s = re.sub(r"_\{(\w)\}", r"_\1", s)
    return s or None


def _decode_image(b64: str):
    import base64
    import io

    from PIL import Image

    raw = base64.b64decode(b64.split(",", 1)[-1], validate=False)
    img = Image.open(io.BytesIO(raw))
    img.load()
    return img.convert("RGB")


def create_app():
    import hmac
    import os
    import threading
    import time

    from fastapi import FastAPI, HTTPException, Request
    from fastapi.responses import JSONResponse
    from pydantic import BaseModel

    started = time.time()
    key = os.environ.get("GPU_KEY", "")
    models = _Models()
    threading.Thread(target=models.load_all, daemon=True).start()
    api = FastAPI(title="DrawExplain GPU", docs_url=None, redoc_url=None, openapi_url=None)

    @api.middleware("http")
    async def require_key(request: Request, call_next):
        got = request.headers.get("x-drawexplain-key", "")
        if not key or not hmac.compare_digest(got.encode(), key.encode()):
            return JSONResponse({"detail": "unauthorized"}, status_code=401)
        return await call_next(request)

    class SegmentRequest(BaseModel):
        image: str
        boxes: list[list[float]]

    class LatexRequest(BaseModel):
        crops: list[str]

    @api.get("/health")
    def health() -> dict:
        import torch

        return {
            "ok": True,
            "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else None,
            "models": {"sam": models.sam is not None, "latex": models.vlm is not None},
            "load_seconds": models.load_seconds,
            "errors": sorted(models.errors),
            "uptime": round(time.time() - started, 1),
        }

    @api.post("/segment")
    def segment(req: SegmentRequest) -> dict:
        t0 = time.perf_counter()
        if not req.boxes:
            return {"results": [], "width": 0, "height": 0, "timings": {}}
        if len(req.boxes) > MAX_BOXES:
            raise HTTPException(400, f"at most {MAX_BOXES} boxes")
        try:
            img = _decode_image(req.image)
        except Exception:
            raise HTTPException(400, "image is not a valid base64 PNG/JPEG") from None
        W, H = img.size
        scale = min(1.0, MAX_SIDE / max(W, H))
        if scale < 1.0:
            img = img.resize((max(1, round(W * scale)), max(1, round(H * scale))))
        w, h = img.size
        boxes, slots = [], []
        for i, b in enumerate(req.boxes):
            if len(b) != 4:
                continue
            x0, y0, x1, y1 = (float(v) * scale for v in b)
            x0, x1 = sorted((max(0.0, min(w - 1.0, x0)), max(0.0, min(w - 1.0, x1))))
            y0, y1 = sorted((max(0.0, min(h - 1.0, y0)), max(0.0, min(h - 1.0, y1))))
            if x1 - x0 >= 2 and y1 - y0 >= 2:
                boxes.append([x0, y0, x1, y1])
                slots.append(i)
        t_decode = time.perf_counter()
        if not models.sam_ready.wait(timeout=90) or models.sam is None:
            raise HTTPException(503, "segmentation model unavailable")
        t_ready = time.perf_counter()
        results: list[dict | None] = [None] * len(req.boxes)
        t_infer = t_ready
        if boxes:
            with models.gpu:
                out = models.sam(img, bboxes=boxes, verbose=False)
            t_infer = time.perf_counter()
            r = out[0]
            masks = r.masks.data.cpu().numpy() if r.masks is not None else []
            confs = r.boxes.conf.cpu().numpy().tolist() if r.boxes is not None else []
            for j, slot in enumerate(slots):
                if j >= len(masks):
                    break
                geo = _mask_geometry(masks[j] > 0.5)
                if geo is None:
                    continue
                if scale < 1.0:
                    geo["box"] = [round(v / scale) for v in geo["box"]]
                    geo["polygon"] = [[round(x / scale), round(y / scale)] for x, y in geo["polygon"]]
                    geo["area"] = round(geo["area"] / (scale * scale))
                geo["score"] = round(float(confs[j]) if j < len(confs) else 0.0, 4)
                results[slot] = geo
        t_end = time.perf_counter()
        return {"results": results, "width": W, "height": H,
                "timings": {"decode": round(t_decode - t0, 3), "wait_model": round(t_ready - t_decode, 3),
                            "infer": round(t_infer - t_ready, 3), "post": round(t_end - t_infer, 3),
                            "total": round(t_end - t0, 3)}}

    @api.post("/latex")
    def latex(req: LatexRequest) -> dict:
        import torch
        from PIL import Image

        t0 = time.perf_counter()
        if len(req.crops) > MAX_CROPS:
            raise HTTPException(400, f"at most {MAX_CROPS} crops")
        if not req.crops:
            return {"latex": [], "timings": {}}
        if not models.vlm_ready.wait(timeout=120) or models.vlm is None:
            raise HTTPException(503, "formula OCR model unavailable")
        t_ready = time.perf_counter()
        imgs, slots = [], []
        for i, b64 in enumerate(req.crops):
            try:
                img = _decode_image(b64)
            except Exception:
                continue
            if img.width >= 1.5 * img.height:  # one formula line: read best at ~64 px tall
                s = LINE_HEIGHT / img.height
                img = img.resize((max(28, min(1600, round(img.width * s))), LINE_HEIGHT), Image.LANCZOS)
            imgs.append(img)
            slots.append(i)
        out: list[str | None] = [None] * len(req.crops)
        if imgs:
            proc = models.proc
            msgs = [{"role": "user", "content": [{"type": "image"}, {"type": "text", "text": LATEX_PROMPT}]}]
            prompt = proc.apply_chat_template(msgs, tokenize=False, add_generation_prompt=True)
            with models.gpu:
                inputs = proc(text=[prompt] * len(imgs), images=imgs, return_tensors="pt", padding=True).to("cuda")
                with torch.inference_mode():
                    ids = models.vlm.generate(**inputs, max_new_tokens=160, do_sample=False)
            texts = proc.batch_decode(ids[:, inputs["input_ids"].shape[1]:], skip_special_tokens=True)
            for slot, text in zip(slots, texts):
                out[slot] = clean_latex(text)
        t_end = time.perf_counter()
        return {"latex": out, "timings": {"wait_model": round(t_ready - t0, 3), "infer": round(t_end - t_ready, 3),
                                          "total": round(t_end - t0, 3)}}

    return api


@app.function(
    gpu="T4",
    secrets=[modal.Secret.from_name(SECRET_NAME)],
    min_containers=0,  # no idle cost: a container starts on demand ...
    max_containers=1,  # ... never more than one (caps spend) ...
    scaledown_window=300,  # ... and stops after 5 idle minutes
    timeout=180,
)
@modal.concurrent(max_inputs=8)
@modal.asgi_app(label=APP_NAME)
def web():
    return create_app()
