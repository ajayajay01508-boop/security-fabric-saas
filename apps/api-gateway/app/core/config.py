from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "postgresql+asyncpg://fabric:fabric_secret@localhost:5432/security_fabric"

    # Redis
    REDIS_URL: str = "redis://localhost:6379"

    # Kafka
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"

    # JWT
    JWT_SECRET_KEY: str = "change-this-secret-key"
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60

    # Stripe
    STRIPE_SECRET_KEY: str = "sk_test_mock"
    STRIPE_WEBHOOK_SECRET: str = "whsec_mock"

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:3000"]

    # Environment
    ENVIRONMENT: str = "development"

    class Config:
        env_file = ".env"


settings = Settings()
