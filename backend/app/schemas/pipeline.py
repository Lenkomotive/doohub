from pydantic import BaseModel


class CreatePipelineRequest(BaseModel):
    repo_path: str
    issue_number: int | None = None
    task_description: str | None = None
    model: str = "claude-opus-4-6"


class PipelineCallbackRequest(BaseModel):
    pipeline_key: str
    status: str
    plan: str | None = None
    branch: str | None = None
    pr_number: int | None = None
    pr_url: str | None = None
    error: str | None = None
    cost_usd: float | None = None
    claude_session_id: str | None = None
    step_log: str | None = None
