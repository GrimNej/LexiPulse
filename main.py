import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, Depends
from fastapi.responses import JSONResponse, HTMLResponse
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database import engine, get_db
from routers import scheduler, feedback, admin, subscribe, unsubscribe, change_topic

# Configure structured logging
logging.basicConfig(
    level=logging.INFO,
    format='{"time":"%(asctime)s","level":"%(levelname)s","name":"%(name)s","message":"%(message)s"}',
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    logger.info("mofa-letter starting up...")
    yield
    # Shutdown
    logger.info("mofa-letter shutting down...")
    await engine.dispose()


app = FastAPI(
    title="mofa-letter",
    description="AI-Powered Custom Newsletter System",
    version="1.0.0",
    lifespan=lifespan,
)


# HTTPS enforcement middleware for sensitive endpoints in production
# Localhost/127.0.0.1 is exempt so the VM cron job can hit the scheduler directly
@app.middleware("http")
async def https_enforcement(request: Request, call_next):
    if settings.env == "production":
        host = request.headers.get("host", "").split(":")[0]
        path = request.url.path
        if path.startswith("/admin") or path.startswith("/scheduler"):
            if request.url.scheme != "https" and host not in ("localhost", "127.0.0.1"):
                return JSONResponse(
                    status_code=400,
                    content={"detail": "HTTPS required"},
                )
    return await call_next(request)


# Register routers
app.include_router(scheduler.router)
app.include_router(feedback.router)
app.include_router(admin.router)
app.include_router(subscribe.router)
app.include_router(unsubscribe.router)
app.include_router(change_topic.router)


LANDING_PAGE_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>mofa-letter — Your Ideas, Delivered Daily</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body {
      font-family: system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
      background: #111827; color: #fff; line-height: 1.6;
    }
    .container { max-width: 720px; margin: 0 auto; padding: 80px 24px; }
    header { text-align: center; margin-bottom: 64px; }
    .brand {
      font-size: 14px; font-weight: 600; letter-spacing: 0.15em;
      text-transform: uppercase; color: #d97706; margin-bottom: 16px;
    }
    h1 { font-size: 56px; font-weight: 700; letter-spacing: -0.02em; margin-bottom: 16px; }
    .tagline { font-size: 22px; color: #e6f4f1; max-width: 560px; margin: 0 auto 32px; }
    .desc { font-size: 16px; color: #9ca3af; max-width: 520px; margin: 0 auto 48px; }
    .cta {
      display: inline-block; padding: 14px 32px; background: #0f766e; color: #fff;
      text-decoration: none; border-radius: 9999px; font-size: 15px; font-weight: 600;
      transition: background 0.2s;
    }
    .cta:hover { background: #0d9488; }
    .features { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 24px; margin-top: 80px; }
    .feature { background: #1f2937; border-radius: 12px; padding: 28px; }
    .feature-num { font-size: 32px; font-weight: 700; color: #0f766e; margin-bottom: 8px; }
    .feature h3 { font-size: 18px; margin-bottom: 8px; }
    .feature p { font-size: 14px; color: #9ca3af; }
    footer { text-align: center; margin-top: 80px; padding-top: 40px; border-top: 1px solid #374151; }
    footer p { font-size: 13px; color: #6b7280; }
    .accent { color: #d97706; }
    @media (max-width: 600px) {
      h1 { font-size: 36px; }
      .tagline { font-size: 18px; }
    }
  </style>
</head>
<body>
  <div class="container">
    <header>
      <p class="brand">AI-Powered Newsletter System</p>
      <h1>mofa-letter.</h1>
      <p class="tagline">Your topic. Your newsletter. Delivered daily.</p>
      <p class="desc">
        Enter any topic — finance, philosophy, cooking, tech, anything.
        Our AI engine crafts a personalized newsletter just for you.
      </p>
      <a href="#" class="cta">Coming Soon — Join the Waitlist</a>
    </header>

    <div class="features">
      <div class="feature">
        <div class="feature-num">01</div>
        <h3>Choose Any Topic</h3>
        <p>Literally anything. From finance to astrophysics. You decide what you want to learn.</p>
      </div>
      <div class="feature">
        <div class="feature-num">02</div>
        <h3>AI Personalization</h3>
        <p>NLP tailors tone, depth, and difficulty. The newsletter adapts to your level and interests over time.</p>
      </div>
      <div class="feature">
        <div class="feature-num">03</div>
        <h3>Daily Delivery</h3>
        <p>Fresh content in your inbox every morning. No fluff. No generic content. Just what you asked for.</p>
      </div>
    </div>

    <footer>
      <p>mofa-letter &middot; Your ideas, delivered daily &middot; Built with <span class="accent">Groq</span> + <span class="accent">Resend</span></p>
    </footer>
  </div>
</body>
</html>
"""


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


@app.get("/", response_class=HTMLResponse)
async def root():
    return HTMLResponse(content=LANDING_PAGE_HTML)
