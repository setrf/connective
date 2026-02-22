from app.connectors.base import BaseConnector
from app.connectors.slack import SlackConnector
from app.connectors.github import GitHubConnector
from app.connectors.google_drive import GoogleDriveConnector


def get_connector(provider: str) -> BaseConnector:
    connectors = {
        "slack": SlackConnector(),
        "github": GitHubConnector(),
        "google_drive": GoogleDriveConnector(),
    }
    if provider not in connectors:
        raise ValueError(f"Unknown provider: {provider}")
    return connectors[provider]
