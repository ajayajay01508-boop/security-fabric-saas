from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    KAFKA_BOOTSTRAP_SERVERS: str = "localhost:9092"
    KAFKA_CONSUMER_GROUP: str = "ai-detection"
    KAFKA_TOPIC_TELEMETRY: str = "raw-telemetry"
    KAFKA_TOPIC_THREATS: str = "threat-events"
    REDIS_URL: str = "redis://localhost:6379"
    MODEL_PATH: str = "models/detector.pkl"
    ENVIRONMENT: str = "development"

    class Config:
        env_file = ".env"


settings = Settings()
