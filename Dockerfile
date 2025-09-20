FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
      build-essential curl && rm -rf /var/lib/apt/lists/*

WORKDIR /app

RUN pip install --no-cache-dir --upgrade pip setuptools wheel
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt \
    --extra-index-url https://download.pytorch.org/whl/cpu

# (Optional but recommended) pre-download the sentence-transformers model into the image layer
# so the first request on Render is fast.
RUN python - <<'PY'\n\
from sentence_transformers import SentenceTransformer\n\
SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')\n\
PY

COPY . .

EXPOSE 8000
# Respect Render's $PORT; default to 8000 locally.
CMD ["sh", "-lc", "uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}"]
