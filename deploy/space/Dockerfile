# MindBridge API on a Hugging Face Docker Space (CPU)
FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends libsndfile1 ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# Spaces run the container as user 1000
RUN useradd -m -u 1000 user
USER user
ENV HOME=/home/user \
    PATH=/home/user/.local/bin:$PATH \
    PYTHONUNBUFFERED=1 \
    ENV=production \
    RISK_MODEL_DIR=/home/user/models/main \
    RISK_MODEL_DIR_EN=/home/user/models/english
WORKDIR /home/user/app

# CPU-only torch keeps the image much smaller than the default CUDA build
RUN pip install --no-cache-dir --user torch==2.2.0 --index-url https://download.pytorch.org/whl/cpu
COPY --chown=user requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

COPY --chown=user . .
EXPOSE 7860
# Models are downloaded from Hugging Face on startup (RISK_MODEL_REPO / RISK_MODEL_REPO_EN)
CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "7860"]
