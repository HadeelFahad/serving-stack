FROM python:3.11-slim

# a non-root user whose home holds the model cache; the run command mounts
# a volume exactly here, so the path must exist and be writable
RUN useradd --create-home app
ENV HF_HOME=/home/app/.cache/huggingface

WORKDIR /app

# requirements layer FIRST: cached across code edits.
# --index-url makes the CPU wheel index authoritative, so pip takes the CPU
# torch (~180 MB) instead of the default CUDA build (~2.5 GB). Without it this
# image is ~6.5 GB and the push takes over an hour on classroom wifi.
COPY app/requirements.txt .
RUN pip install --no-cache-dir \
      --index-url https://download.pytorch.org/whl/cpu --extra-index-url https://pypi.org/simple \
      -r requirements.txt   # versions per ../../PINS.md

# code SECOND: this is the layer that changes every edit
COPY app/ .

RUN mkdir -p /home/app/.cache/huggingface && chown -R app:app /home/app/.cache /app


USER app

EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]