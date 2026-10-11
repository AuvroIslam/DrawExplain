# StudyLens / DrawExplain API (FastAPI + RapidOCR + OpenCV + PyMuPDF) for Render or any container host.
# The frontend is deployed separately (Vercel) and calls this API through VITE_API_BASE.
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1

# libgl1 + libglib2.0-0: OpenCV (pulled in by RapidOCR); DejaVu: readable region tags on the Set-of-Mark image
RUN apt-get update \
    && apt-get install -y --no-install-recommends libgl1 libglib2.0-0 fonts-dejavu-core \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app
COPY backend/requirements.txt backend/requirements.txt
RUN pip install -r backend/requirements.txt

COPY backend/ backend/
COPY samples/ samples/

WORKDIR /app/backend
ENV SERVE_FRONTEND=0 \
    LLM_CACHE=1 \
    PORT=8000
EXPOSE 8000
CMD ["sh", "-c", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT} --proxy-headers --forwarded-allow-ips='*'"]
