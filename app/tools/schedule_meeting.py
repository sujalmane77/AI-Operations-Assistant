"""
Google Calendar API tool. Respects DRY_RUN the same way as send_email.
"""
from app.tools.base import register_tool
from app.config import config

SCOPES = ["https://www.googleapis.com/auth/calendar.events"]


def _get_calendar_service():
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

    return build("calendar", "v3", credentials=creds)


@register_tool(
    name="schedule_meeting",
    description="Create a Google Calendar event (or log it in dry-run mode).",
    input_schema={
        "title": "meeting title",
        "start_time": "ISO 8601 start datetime, e.g. 2026-09-20T15:00:00",
        "end_time": "ISO 8601 end datetime, e.g. 2026-09-20T15:30:00",
        "attendees": "optional comma-separated list of attendee emails",
    },
)
def schedule_meeting(title: str, start_time: str, end_time: str, attendees: str = "") -> dict:
    if config.dry_run:
        return {
            "dry_run": True,
            "title": title,
            "start_time": start_time,
            "end_time": end_time,
            "attendees": attendees,
            "note": "DRY_RUN is enabled — event was NOT actually created.",
        }

    service = _get_calendar_service()
    event = {
        "summary": title,
        "start": {"dateTime": start_time},
        "end": {"dateTime": end_time},
    }
    if attendees:
        event["attendees"] = [{"email": e.strip()} for e in attendees.split(",") if e.strip()]

    created = service.events().insert(calendarId="primary", body=event).execute()
    return {"dry_run": False, "title": title, "event_id": created.get("id"), "link": created.get("htmlLink")}
