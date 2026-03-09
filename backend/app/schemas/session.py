from pydantic import BaseModel


class CreateSessionRequest(BaseModel):
    name: str | None = None
    model: str = "claude-opus-4-6"
    project_path: str = ""
    mode: str = "oneshot"


class SendMessageRequest(BaseModel):
    content: str
