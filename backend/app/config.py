from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    app_env: str = "development"
    secret_key: str = "change-me"
    access_token_expire_minutes: int = 43200
    database_url: str = "sqlite:///./grind_advisor.db"
    frontend_origin: str = "http://localhost:5173"
    model_dir: str = "./data/models"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

settings = Settings()
