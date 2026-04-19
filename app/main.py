from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app.database import init_db
from app.utils.logger import logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    Path("data").mkdir(exist_ok=True)
    Path("data/logs").mkdir(exist_ok=True)
    Path("data/uploads").mkdir(exist_ok=True)
    Path("data/cookies").mkdir(exist_ok=True)

    await init_db()
    logger.info("Database initialized")

    from app.ai_gateway.registry import registry
    from app.ai_gateway.providers.doubao_adapter import DoubaoAdapter
    from app.ai_gateway.providers.wanx_adapter import WanxAdapter
    from app.ai_gateway.providers.seedance_adapter import SeedanceAdapter
    from app.ai_gateway.providers.nano_banana_adapter import NanoBananaAdapter
    from app.ai_gateway.providers.glm_adapter import QwenAdapter

    registry.register(DoubaoAdapter())
    registry.register(WanxAdapter())
    registry.register(SeedanceAdapter())
    registry.register(NanoBananaAdapter())
    registry.register(QwenAdapter())
    logger.info(f"Registered {len(registry.list_providers())} AI providers")

    yield


app = FastAPI(
    title="AI Creator Studio Server",
    version="1.0.0",
    description="AI-powered short video creation platform",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ─── Global exception handlers ─────────────────────────────────────────────

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    import traceback
    logger.error(f"Unhandled exception on {request.method} {request.url.path}: {exc}\n{traceback.format_exc()}")
    return JSONResponse(
        status_code=500,
        content={"detail": str(exc)},
    )


@app.exception_handler(ValueError)
async def value_error_handler(request: Request, exc: ValueError):
    return JSONResponse(
        status_code=400,
        content={"detail": str(exc)},
    )


@app.exception_handler(RuntimeError)
async def runtime_error_handler(request: Request, exc: RuntimeError):
    return JSONResponse(
        status_code=502,
        content={"detail": str(exc)},
    )


# ─── Health check ───────────────────────────────────────────────────────────

@app.get("/health", tags=["System"])
async def health_check():
    return {"status": "ok", "version": "1.0.0"}


# ─── Register all API routers ────────────────────────────────────────────────

from app.api.v1.auth import router as auth_router  # noqa: E402
from app.api.v1.projects import router as projects_router  # noqa: E402
from app.api.v1.scripts import router as scripts_router  # noqa: E402
from app.api.v1.storyboards import router as storyboards_router  # noqa: E402
from app.api.v1.characters import router as characters_router  # noqa: E402
from app.api.v1.generation import router as generation_router  # noqa: E402
from app.api.v1.assets import router as assets_router  # noqa: E402
from app.api.v1.publishing import router as publishing_router  # noqa: E402
from app.api.v1.knowledge import router as knowledge_router  # noqa: E402
from app.api.v1.analytics import router as analytics_router  # noqa: E402
from app.api.v1.ai_gateway import router as ai_gateway_router  # noqa: E402
from app.api.v1.cookies import router as cookies_router  # noqa: E402

app.include_router(auth_router, prefix="/api/v1")
app.include_router(projects_router, prefix="/api/v1")
app.include_router(scripts_router, prefix="/api/v1")
app.include_router(storyboards_router, prefix="/api/v1")
app.include_router(characters_router, prefix="/api/v1")
app.include_router(generation_router, prefix="/api/v1")
app.include_router(assets_router, prefix="/api/v1")
app.include_router(publishing_router, prefix="/api/v1")
app.include_router(knowledge_router, prefix="/api/v1")
app.include_router(analytics_router, prefix="/api/v1")
app.include_router(ai_gateway_router, prefix="/api/v1/ai")
app.include_router(cookies_router, prefix="/api/v1")

# Static files for analysis thumbnails and reports
Path("data/analysis").mkdir(parents=True, exist_ok=True)
app.mount("/static/analysis", StaticFiles(directory="data/analysis"), name="analysis_static")
app.mount("/static/uploads", StaticFiles(directory="data/uploads"), name="uploads_static")
