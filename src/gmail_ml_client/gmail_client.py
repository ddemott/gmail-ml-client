import os
from typing import Any

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

from .logger import logger

SCOPES = [
    "https://www.googleapis.com/auth/gmail.modify",
    "https://www.googleapis.com/auth/gmail.labels",
]


def _token_path() -> str:
    return "token.json"


def get_service() -> Any:
    """Get authenticated Gmail service with error handling."""
    try:
        creds = None
        if os.path.exists(_token_path()):
            creds = Credentials.from_authorized_user_file(_token_path(), SCOPES)

        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                logger.info("Refreshing expired credentials")
                creds.refresh(Request())
            else:
                if not os.path.exists("credentials.json"):
                    logger.error("credentials.json not found")
                    raise FileNotFoundError(
                        "credentials.json not found. Please:\n"
                        "1. Go to https://console.cloud.google.com/\n"
                        "2. Enable Gmail API\n"
                        "3. Create OAuth client credentials\n"
                        "4. Download as 'credentials.json' in project root"
                    )
                logger.info("Starting OAuth flow")
                flow = InstalledAppFlow.from_client_secrets_file("credentials.json", SCOPES)
                creds = flow.run_local_server(port=0)

            with open(_token_path(), "w") as token:
                token.write(creds.to_json())
                logger.info("Saved credentials to token.json")

        return build("gmail", "v1", credentials=creds)
    except Exception as e:
        logger.error(f"Failed to get Gmail service: {e}")
        raise


def list_messages(
    query: str | None = None, label_ids: list[str] | None = None, max_results: int = 100
) -> list[dict[str, str]]:
    """List Gmail messages with error handling."""
    try:
        svc = get_service()
        user_id = "me"
        req = (
            svc.users()
            .messages()
            .list(userId=user_id, q=query, labelIds=label_ids, maxResults=max_results)
        )
        msgs = []

        while req is not None:
            resp = req.execute()
            msgs.extend(resp.get("messages", []))
            req = svc.users().messages().list_next(req, resp)
            if len(msgs) >= max_results:
                break

        logger.info(f"Listed {len(msgs)} messages")
        return msgs[:max_results]
    except HttpError as e:
        logger.error(f"Gmail API error listing messages: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error listing messages: {e}")
        raise


def get_message(msg_id: str) -> dict[str, Any]:
    """Get a specific Gmail message with error handling."""
    try:
        svc = get_service()
        return svc.users().messages().get(userId="me", id=msg_id, format="full").execute()
    except HttpError as e:
        logger.error(f"Gmail API error getting message {msg_id}: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error getting message {msg_id}: {e}")
        raise


def modify_labels(
    msg_id: str, add: list[str] | None = None, remove: list[str] | None = None
) -> dict[str, Any]:
    """Modify labels on a Gmail message with error handling."""
    try:
        svc = get_service()
        body = {"addLabelIds": add or [], "removeLabelIds": remove or []}
        result = svc.users().messages().modify(userId="me", id=msg_id, body=body).execute()
        logger.debug(f"Modified labels for message {msg_id}: +{add} -{remove}")
        return result
    except HttpError as e:
        logger.error(f"Gmail API error modifying labels for {msg_id}: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error modifying labels for {msg_id}: {e}")
        raise


def trash_message(msg_id: str) -> dict[str, Any]:
    """Move a Gmail message to trash with error handling."""
    try:
        svc = get_service()
        result = svc.users().messages().trash(userId="me", id=msg_id).execute()
        logger.info(f"Moved message {msg_id} to trash")
        return result
    except HttpError as e:
        logger.error(f"Gmail API error trashing message {msg_id}: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error trashing message {msg_id}: {e}")
        raise


def get_labels() -> list[dict[str, str]]:
    """Get all Gmail labels with error handling."""
    try:
        svc = get_service()
        resp = svc.users().labels().list(userId="me").execute()
        labels = resp.get("labels", [])
        logger.debug(f"Retrieved {len(labels)} labels")
        return labels
    except HttpError as e:
        logger.error(f"Gmail API error getting labels: {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error getting labels: {e}")
        raise


def ensure_label(name: str) -> str:
    """Ensure a Gmail label exists, creating if necessary."""
    try:
        svc = get_service()
        labels = get_labels()

        # Check if label already exists
        for l in labels:
            if l["name"] == name:
                logger.debug(f"Label '{name}' already exists with ID {l['id']}")
                return l["id"]

        # Create new label
        body = {"name": name, "labelListVisibility": "labelShow", "messageListVisibility": "show"}
        created = svc.users().labels().create(userId="me", body=body).execute()
        logger.info(f"Created new label '{name}' with ID {created['id']}")
        return created["id"]
    except HttpError as e:
        logger.error(f"Gmail API error ensuring label '{name}': {e}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error ensuring label '{name}': {e}")
        raise
