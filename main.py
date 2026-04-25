import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database import engine, get_db
from routers import scheduler, feedback, admin

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='{"time":"%(asctime)s","level":"%(levelname)s","name":"%(name)s","message":"%(message)s"}',
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("LexiPulse starting up...")
    yield
    # Shutdown
    logger.info("LexiPulse shutting down...")
    await engine.dispose()


app = FastAPI(
    title="LexiPulse",
    description="Adaptive Daily Vocabulary Newsletter",
    version="1.0.0",
    lifespan=lifespan,
)


# HTTPS enforcement middleware for sensitive endpoints in production
@app.middleware("http")
async def https_enforcement(request: Request, call_next):
    if settings.env == "production":
        path = request.url.path
        if path.startswith("/admin") or path.startswith("/scheduler"):
            if request.url.scheme != "https":
                return JSONResponse(
                    status_code=400,
                    content={"detail": "HTTPS required"},
                )
    return await call_next(request)


# Register routers
app.include_router(scheduler.router)
app.include_router(feedback.router)
app.include_router(admin.router)


@app.get("/health", response_model=dict)
async def health_check(db: AsyncSession = Depends(get_db)):
    try:
        result = await db.execute(text("SELECT 1"))
        result.scalar_one()
        return {"status": "ok", "database": "connected"}
    except Exception as exc:
        logger.error(f"Health check failed: {exc}")
        return JSONResponse(
            status_code=503,
            content={"status": "error", "database": "disconnected"},
        )


@app.get("/")
async def root():
    return {"app": "LexiPulse", "version": "1.0.0"}
