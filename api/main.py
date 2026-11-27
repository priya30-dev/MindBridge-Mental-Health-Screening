import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src import model_loader

from api.db import init_db
from api.state import models  # shared model storage (re-exported for old imports)
from api.routers import (
    text, audio, auth, checkins, journal, questionnaires, comfort, report, privacy, counsellor,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()

    # Loads whichever trained models exist; missing ones are skipped with a
    # clear message instead of crashing the server.
    models.update(model_loader.load_available_models())

    import threading
    from api.services import warm_up
    threading.Thread(target=warm_up, daemon=True).start()

    yield

    models.clear()
    print("Models unloaded.")


app = FastAPI(
    title="MindBridge API",
    description="Real-time Mental Health Crisis Detection",
    version="2.0.0",
    lifespan=lifespan,
)

# Only allow known frontends. Set ALLOWED_ORIGINS in .env as a
# comma-separated list for production (e.g. your deployed dashboard URL).
ALLOWED_ORIGINS = [
    o.strip()
    for o in os.getenv(
        "ALLOWED_ORIGINS", "http://localhost:8501,http://127.0.0.1:8501"
    ).split(",")
    if o.strip()
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(
    text.router,
    prefix="/api/v1/text",
    tags=["Text Analysis"],
)

app.include_router(
    audio.router,
    prefix="/api/v1/audio",
    tags=["Audio Analysis"],
)

# Platform features (require login)
app.include_router(auth.router, prefix="/api/v1/auth", tags=["Accounts"])
app.include_router(checkins.router, prefix="/api/v1/checkins", tags=["Check-ins"])
app.include_router(journal.router, prefix="/api/v1/journal", tags=["Journal"])
app.include_router(questionnaires.router, prefix="/api/v1/questionnaires", tags=["PHQ-9 / GAD-7"])
app.include_router(comfort.router, prefix="/api/v1/comfort", tags=["Chill zone"])
app.include_router(report.router, prefix="/api/v1/report", tags=["Reports"])
app.include_router(privacy.router, prefix="/api/v1/me/data", tags=["Privacy"])
app.include_router(counsellor.router, prefix="/api/v1/counsellor", tags=["Counsellor"])


@app.get("/")
def root():
    return {
        "message": "MindBridge API Running"
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
        "text_model": "risk" if "risk_model" in models else "emotion" if "text_model" in models else None,
        "languages": __import__("api.services", fromlist=["x"]).model_languages(),
        "language_routing": "risk_model_en" in models,
        "voice_model": "audio_model" in models,
    }