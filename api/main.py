from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.text_model import load_text_model
from src.audio_model import load_audio_model

# Routers
from api.routers import text, audio


# Shared model storage
models = {}


@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Loading text model...")
    tokenizer, text_model = load_text_model()

    models["tokenizer"] = tokenizer
    models["text_model"] = text_model

    print("Loading audio model...")
    audio_model, scaler = load_audio_model()

    models["audio_model"] = audio_model
    models["audio_scaler"] = scaler

    print("All models loaded successfully.")

    yield

    models.clear()
    print("Models unloaded.")


app = FastAPI(
    title="MindBridge API",
    description="Real-time Mental Health Crisis Detection",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
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


@app.get("/")
def root():
    return {
        "message": "MindBridge API Running"
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
        "models_loaded": bool(models)
    }