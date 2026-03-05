from pydantic import BaseModel


class LoginRequest(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class FcmTokenRequest(BaseModel):
    token: str


class NotificationSettingsRequest(BaseModel):
    notify_sessions: bool
    notify_pipelines: bool


class NotificationSettingsResponse(BaseModel):
    notify_sessions: bool
    notify_pipelines: bool

    model_config = {"from_attributes": True}


class UserResponse(BaseModel):
    id: int
    username: str

    model_config = {"from_attributes": True}
