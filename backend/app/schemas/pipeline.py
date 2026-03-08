from pydantic import BaseModel


class CreatePipelineRequest(BaseModel):
    repo_path: str
    issue_number: int | None = None
    task_description: str | None = None
    model: str = "claude-opus-4-6"
    template_id: int | None = None


class StepLog(BaseModel):
    node_id: str
    node_name: str
    node_type: str
    status: str  # "running", "completed", "failed", "skipped"
    started_at: str | None = None
    completed_at: str | None = None
    duration_s: float | None = None
    output: str | None = None  # extracted output summary
    error: str | None = None


class PipelineCallbackRequest(BaseModel):
    pipeline_key: str
    status: str
    issue_title: str | None = None
    plan: str | None = None
    branch: str | None = None
    pr_number: int | None = None
    pr_url: str | None = None
    error: str | None = None
    cost_usd: float | None = None
    input_tokens: int | None = None
    output_tokens: int | None = None
    claude_session_id: str | None = None
    step_log: str | None = None
    step: StepLog | None = None
