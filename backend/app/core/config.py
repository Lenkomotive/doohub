from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    app_name: str = "DooHub"
    database_url: str = "postgresql://doohub:doohub@db:5432/doohub"
    secret_key: str = "change-me-in-production"
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 15
    refresh_token_expire_days: int = 7
    provider_url: str = "http://slave:8001"
    provider_api_key: str = "change-me"

    model_config = {"env_prefix": "DOOHUB_"}


settings = Settings()
