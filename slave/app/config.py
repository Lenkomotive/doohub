from pathlib import Path

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    api_key: str = "change-me"
    projects_dir: Path = Path("/projects")
    data_dir: Path = Path("/data")
    claude_md_src: Path = Path("/app/claude-md/CLAUDE.md")
    log_level: str = "INFO"

    model_config = {"env_prefix": "SLAVE_"}


settings = Settings()
