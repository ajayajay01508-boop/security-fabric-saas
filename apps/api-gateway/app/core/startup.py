"""
Startup validation: fails fast if the environment is misconfigured.
Called from main.py lifespan before accepting traffic.
"""
import logging
import os
import sys

logger = logging.getLogger("startup")

REQUIRED_ENV_VARS = [
    "DATABASE_URL",
    "REDIS_URL",
    "KAFKA_BOOTSTRAP_SERVERS",
    "JWT_SECRET_KEY",
]

WEAK_SECRETS = {
    "change-this-secret-key",
    "super-secret-jwt-key-change-in-production",
    "secret",
    "password",
    "test",
    "",
}


def validate_environment():
    """Validate all required environment variables are present and sane."""
    errors = []
    warnings = []

    for var in REQUIRED_ENV_VARS:
        val = os.getenv(var)
        if not val:
            errors.append(f"Required environment variable '{var}' is not set")

    jwt_secret = os.getenv("JWT_SECRET_KEY", "")
    env = os.getenv("ENVIRONMENT", "development")

    if env == "production":
        if jwt_secret in WEAK_SECRETS:
            errors.append("JWT_SECRET_KEY is a known weak/default value — set a strong secret")
        if len(jwt_secret) < 32:
            errors.append(f"JWT_SECRET_KEY too short ({len(jwt_secret)} chars) — use at least 32 characters")
        if os.getenv("STRIPE_SECRET_KEY", "").startswith("sk_test_"):
            warnings.append("STRIPE_SECRET_KEY is a test key in production environment")
    else:
        if jwt_secret in WEAK_SECRETS:
            warnings.append("JWT_SECRET_KEY is a weak default — fine for dev, must change for prod")

    db_url = os.getenv("DATABASE_URL", "")
    if db_url and "localhost" in db_url and env == "production":
        warnings.append("DATABASE_URL points to localhost in production")

    for w in warnings:
        logger.warning(f"[startup] ⚠  {w}")

    if errors:
        for e in errors:
            logger.error(f"[startup] ✗  {e}")
        env = os.getenv("ENVIRONMENT", "development")
        if env == "production":
            logger.error(f"[startup] {len(errors)} startup error(s). Aborting.")
            sys.exit(1)
        else:
            logger.warning(f"[startup] {len(errors)} startup issue(s) ignored in {env} mode.")

    logger.info(f"[startup] ✓  Environment validated (env={env})")


def log_startup_banner():
    env = os.getenv("ENVIRONMENT", "development")
    logger.info("=" * 55)
    logger.info("  SECURITY FABRIC — API GATEWAY")
    logger.info(f"  Environment : {env.upper()}")
    logger.info(f"  DB          : {os.getenv('DATABASE_URL','').split('@')[-1]}")
    logger.info(f"  Redis       : {os.getenv('REDIS_URL','')}")
    logger.info(f"  Kafka       : {os.getenv('KAFKA_BOOTSTRAP_SERVERS','')}")
    logger.info("=" * 55)
