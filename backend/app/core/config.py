from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional, List, Dict, Any
import os

class Settings(BaseSettings):
    # App Settings
    PROJECT_NAME: str = "CarBrain Backend"
    API_V1_STR: str = "/api"
    ENV: str = "development"
    PORT: int = 5000

    # JWT Settings
    JWT_SECRET: str
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # Database Settings
    DATABASE_URL: str

    # MQTT Settings
    MQTT_HOST: str = "localhost"
    MQTT_PORT: int = 1883
    MQTT_USER: Optional[str] = None
    MQTT_PASSWORD: Optional[str] = None
    MQTT_TOPIC_DTC: str = "vehicle/+/dtc"
    
    # Mailer Settings (Migrating from mailer.js)
    MAIL_HOST: Optional[str] = None
    MAIL_PORT: int = 587
    MAIL_USER: Optional[str] = None
    MAIL_PASSWORD: Optional[str] = None
    MAIL_FROM: Optional[str] = None
    
    # LLM Settings (Remote Agentic Workflow)
    LLM_BASE_URL: str = "http://localhost:8000"
    LLM_API_KEY: Optional[str] = None
    LLM_ANALYZE_PATH: str = "/api/llm/analyze"
    LLM_CHAT_PATH: str = "/api/llm/chat"

    model_config = SettingsConfigDict(env_file=".env", case_sensitive=True, extra="ignore")

settings = Settings()
