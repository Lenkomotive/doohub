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
    claude_session_id: str | None = None
    step_log: str | None = None
    step: StepLog | None = None


# --- Monitoring response schemas ---


class PipelineEvent(BaseModel):
    event_type: str
    pipeline_key: str
    status: str
    node_id: str | None = None
    node_name: str | None = None
    cost_usd: float | None = None
    timestamp: str


class DashboardSummary(BaseModel):
    running: int
    completed: int
    failed: int
    total: int


class DashboardPipeline(BaseModel):
    pipeline_key: str
    issue_number: int | None = None
    issue_title: str | None = None
    repo_path: str
    status: str
    current_node: str | None = None
    model: str
    total_cost_usd: float
    duration_s: float | None = None
    started_at: str
    updated_at: str


class DashboardResponse(BaseModel):
    summary: DashboardSummary
    pipelines: list[DashboardPipeline]


class StepsResponse(BaseModel):
    pipeline_key: str
    status: str
    steps: list[dict]
