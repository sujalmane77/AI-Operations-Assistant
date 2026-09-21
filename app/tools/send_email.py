"""
Gmail API tool. Respects DRY_RUN (default true) — when true, does not
actually send, just logs the composed email so testing never spams a
real inbox.
"""
import base64
from email.mime.text import MIMEText

from app.tools.base import register_tool
from app.config import config

SCOPES = ["https://www.googleapis.com/auth/gmail.send"]


def _get_gmail_service():
    import os
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build

    creds = None
    if os.path.exists(config.google_token_path):
        creds = Credentials.from_authorized_user_file(config.google_token_path, SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(config.google_credentials_path, SCOPES)
            creds = flow.run_local_server(port=0)
        with open(config.google_token_path, "w") as f:
            f.write(creds.to_json())

    return build("gmail", "v1", credentials=creds)


@register_tool(
    name="send_email",
    description="Send an email via Gmail (or log it in dry-run mode).",
    input_schema={
        "to": "recipient email address",
        "subject": "email subject line",
        "body": "email body text",
    },
)
def send_email(to: str, subject: str, body: str) -> dict:
    if config.dry_run:
        return {
            "dry_run": True,
            "to": to,
            "subject": subject,
            "body": body,
            "note": "DRY_RUN is enabled — email was NOT actually sent.",
        }

    service = _get_gmail_service()
    message = MIMEText(body)
    message["to"] = to
    message["subject"] = subject
    raw = base64.urlsafe_b64encode(message.as_bytes()).decode()

    sent = service.users().messages().send(userId="me", body={"raw": raw}).execute()
    return {"dry_run": False, "to": to, "subject": subject, "message_id": sent.get("id")}
