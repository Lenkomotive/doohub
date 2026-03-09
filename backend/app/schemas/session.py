from pydantic import BaseModel


VALID_MODES = {"planning", "interactive", "workflow", "issue_creation", "chat"}


class CreateSessionRequest(BaseModel):
    name: str | None = None
    model: str = "claude-opus-4-6"
    project_path: str
    mode: str = "chat"


class SendMessageRequest(BaseModel):
    content: str
