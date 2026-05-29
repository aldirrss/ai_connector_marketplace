import logging
import time
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from backend.routers.registry_router import router as registry_router
from backend.routers.installer_router import router as installer_router
from backend.core.config_manager import get_config_path_info
from backend.services.registry_service import get_registry_stats

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s — %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("AI Connector Marketplace backend starting…")
    cfg = get_config_path_info()
    logger.info("Claude config path: %s (exists=%s)", cfg["path"], cfg["exists"])
    stats = get_registry_stats()
    logger.info("Registry loaded — %d MCPs, %d installed", stats.total, stats.installed)
    yield
    logger.info("Backend shutting down")


app = FastAPI(
    title="AI Connector Marketplace",
    description=(
        "Local MCP Manager — browse, install, and configure MCP servers "
        "for Claude Desktop from a single web interface."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        # Web dev server (Phase 2)
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        # Tauri desktop webview origins (Phase 5). The packaged app serves the
        # static frontend from a custom protocol, not localhost:3000.
        "tauri://localhost",
        "https://tauri.localhost",
        "http://tauri.localhost",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start) * 1000
    logger.info("%s %s → %d (%.1fms)", request.method, request.url.path, response.status_code, duration_ms)
    return response


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error("Unhandled error on %s %s: %s", request.method, request.url.path, exc, exc_info=True)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error", "error": str(exc)},
    )


app.include_router(registry_router)
app.include_router(installer_router)


@app.get("/", tags=["health"])
async def root() -> dict:
    return {
        "name": "AI Connector Marketplace",
        "version": "1.0.0",
        "status": "running",
        "docs": "/docs",
    }


@app.get("/health", tags=["health"])
async def health() -> dict:
    stats = get_registry_stats()
    cfg = get_config_path_info()
    return {
        "status": "ok",
        "registry": {"total": stats.total, "installed": stats.installed},
        "claude_config": cfg,
    }
