from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    """Application configuration from environment variables."""
    
    # Supabase
    supabase_url: str
    supabase_publishable_key: str
    supabase_secret_key: str
    
    # APIs
    data_gov_in_api_key: str = ""
    openmeteo_api_url: str = "https://api.open-meteo.com/v1"
    
    # Admin
    ingest_admin_token: str
    
    # CORS
    cors_origins: List[str] = ["http://localhost:3000", "http://localhost:5173"]
    
    # Server
    debug: bool = True
    port: int = 8000
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()
