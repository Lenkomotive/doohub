from pydantic import BaseModel


class CreateSessionRequest(BaseModel):
    session_key: str
    model: str = "sonnet"
    project_path: str
    interactive: bool = False


class SendMessageRequest(BaseModel):
    content: str
