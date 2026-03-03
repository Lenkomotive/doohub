from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "DooHub"
    database_url: str = "postgresql://doohub:doohub@db:5432/doohub"
    secret_key: str = "change-me-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    slave_url: str = "http://slave:8001"
    slave_api_key: str = "change-me"
    backend_internal_url: str = "http://backend:8000"

    model_config = {"env_prefix": "DOOHUB_"}


settings = Settings()
