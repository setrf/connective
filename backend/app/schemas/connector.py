import datetime
import uuid
from pydantic import BaseModel


class ConnectorResponse(BaseModel):
    id: uuid.UUID
    provider: str
    status: str
    last_synced_at: datetime.datetime | None
    error_message: str | None
    config: dict | None


class ConnectorConfigUpdate(BaseModel):
    config: dict


class OAuthURLResponse(BaseModel):
    url: str


class GitHubRepoItem(BaseModel):
    full_name: str
    description: str | None
    private: bool
    updated_at: str | None
    language: str | None
    stargazers_count: int


class GoogleDriveFolderItem(BaseModel):
    id: str
    name: str


class IngestStatusResponse(BaseModel):
    provider: str
    status: str
    last_synced_at: datetime.datetime | None
    error_message: str | None
