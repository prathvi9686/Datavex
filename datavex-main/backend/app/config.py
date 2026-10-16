"""
DataVex Backend — Configuration
Loads settings from .env file via pydantic-settings.
"""
from pydantic_settings import BaseSettings
from functools import lru_cache
import os

class Settings(BaseSettings):
    # Bytez / LLM
    bytez_api_key: str = ""
    bytez_model: str = "openai/gpt-4.1"
    bytez_base_url: str = "https://api.bytez.com/models/v2/openai/v1"

    # Database
    database_url: str = "sqlite:///./datavex.db"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    class Config:
        env_file = os.path.join(os.path.dirname(os.path.dirname(__file__)), ".env")
        env_file_encoding = "utf-8"

@lru_cache()
def get_settings() -> Settings:
    return Settings()
