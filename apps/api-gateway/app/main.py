from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from app.database import init_db
from app.routers import auth, alerts, payments, telemetry, websocket, metrics, admin
from app.services.kafka_service import kafka_producer
from app.services.redis_service import redis_client
from app.middleware.logging import RequestLoggingMiddleware
from app.middleware.rate_limit import RateLimitMiddleware
from app.core.config import settings
from app.core.startup import validate_environment, log_startup_banner


@asynccontextmanager
async def lifespan(app: FastAPI):
    validate_environment()
    log_startup_banner()
    await init_db()
    await kafka_producer.start()
    yield
    await kafka_producer.stop()
    await redis_client.close()


app = FastAPI(
    title="Security Fabric API Gateway",
    description="Real-time threat detection and security intelligence platform",
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(RateLimitMiddleware, redis_client=redis_client)

app.include_router(auth.router,      prefix="/auth",      tags=["Authentication"])
app.include_router(alerts.router,    prefix="/alerts",    tags=["Alerts"])
app.include_router(payments.router,  prefix="/payments",  tags=["Payments"])
app.include_router(telemetry.router, prefix="/telemetry", tags=["Telemetry"])
app.include_router(websocket.router, prefix="/ws",        tags=["WebSocket"])
app.include_router(metrics.router,                        tags=["Observability"])
app.include_router(admin.router,    prefix="/admin",     tags=["Admin"])


@app.get("/health", tags=["Health"])
async def health_check():
    return {"status": "healthy", "service": "api-gateway", "version": "1.0.0"}


@app.get("/", include_in_schema=False)
async def root():
    return {"message": "Security Fabric API Gateway", "docs": "/docs"}
