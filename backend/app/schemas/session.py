from pydantic import BaseModel


from typing import Literal


class CreateSessionRequest(BaseModel):
    name: str | None = None
    model: str = "claude-opus-4-6"
    project_path: str = ""
    mode: Literal["oneshot", "planning", "analysis", "freeform"] = "oneshot"


class SendMessageRequest(BaseModel):
    content: str
