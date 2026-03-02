from datetime import datetime

from pydantic import BaseModel


class CreateSessionRequest(BaseModel):
    session_key: str
    model: str = "sonnet"
    project_path: str
    interactive: bool = False


class SendMessageRequest(BaseModel):
    content: str


class SendMessageResponse(BaseModel):
    role: str
    content: str
    session_id: str | None = None
    cost_usd: float | None = None


class PipelineResponse(BaseModel):
    id: int
    pipeline_key: str
    repo: str
    repo_path: str
    issue_number: int
    issue_title: str
    status: str
    pr_number: int | None
    branch: str | None
    review_round: int
    plan: str | None
    error: str | None
    started_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class PipelineListResponse(BaseModel):
    pipelines: list[PipelineResponse]
    total: int
