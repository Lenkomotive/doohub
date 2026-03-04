from pydantic import BaseModel


class CreateSessionRequest(BaseModel):
    name: str
    model: str = "claude-opus-4-6"
    project_path: str
    interactive: bool = False


class SendMessageRequest(BaseModel):
    content: str
    images: list[str] | None = None
