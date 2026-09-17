import json
import logging
import os
from typing import Optional

logger = logging.getLogger(__name__)

_sheets_service = None


def _get_service():
    """Lazy-initialise the Google Sheets API client from service account JSON."""
    global _sheets_service
    if _sheets_service is not None:
        return _sheets_service

    sa_json = os.environ.get("GOOGLE_SERVICE_ACCOUNT_JSON", "").strip()
    if not sa_json:
        logger.info("GOOGLE_SERVICE_ACCOUNT_JSON not set — Sheets sync disabled.")
        return None

    try:
        from google.oauth2.service_account import Credentials
        from googleapiclient.discovery import build

        creds = Credentials.from_service_account_info(
            json.loads(sa_json),
            scopes=["https://www.googleapis.com/auth/spreadsheets"],
        )
        _sheets_service = build("sheets", "v4", credentials=creds, cache_discovery=False)
        return _sheets_service
    except Exception as exc:
        logger.exception(f"Failed to init Sheets API: {exc}")
        return None


def _spreadsheet_id() -> Optional[str]:
    return os.environ.get("SHEETS_SPREADSHEET_ID") or None


def ensure_sheet_headers() -> bool:
    """Create header row in the 'Clients' sheet if absent."""
    svc = _get_service()
    sid = _spreadsheet_id()
    if not svc or not sid:
        return False
    try:
        result = svc.spreadsheets().values().get(
            spreadsheetId=sid, range="Clients!A1:I1"
        ).execute()
        if not result.get("values"):
            headers = [["ID", "Name", "Email", "Phone", "Segment", "Risk Level", "Urgency", "Status", "Created At"]]
            svc.spreadsheets().values().update(
                spreadsheetId=sid,
                range="Clients!A1:I1",
                valueInputOption="RAW",
                body={"values": headers},
            ).execute()
        return True
    except Exception as exc:
        logger.exception(f"ensure_sheet_headers failed: {exc}")
        return False


def sync_client_to_sheet(client) -> bool:
    """Write/update a client row in the master Google Sheet. Returns True on success."""
    svc = _get_service()
    sid = _spreadsheet_id()
    if not svc or not sid:
        return False

    try:
        row = [
            client.id,
            client.name,
            client.email or "",
            client.phone or "",
            client.segment.name if client.segment else "",
            client.risk_level or "",
            client.urgency or "",
            client.status or "active",
            client.created_at.strftime("%Y-%m-%d %H:%M:%S"),
        ]
        existing = _find_row(svc, sid, client.id)
        if existing:
            svc.spreadsheets().values().update(
                spreadsheetId=sid,
                range=f"Clients!A{existing}:I{existing}",
                valueInputOption="RAW",
                body={"values": [row]},
            ).execute()
        else:
            svc.spreadsheets().values().append(
                spreadsheetId=sid,
                range="Clients!A:I",
                valueInputOption="RAW",
                insertDataOption="INSERT_ROWS",
                body={"values": [row]},
            ).execute()
        logger.info(f"Sheets sync OK — client {client.id}")
        return True
    except Exception as exc:
        logger.exception(f"Sheets sync failed for client {client.id}: {exc}")
        return False


def _find_row(svc, sid: str, client_id: str) -> Optional[int]:
    try:
        result = svc.spreadsheets().values().get(
            spreadsheetId=sid, range="Clients!A:A"
        ).execute()
        for i, row in enumerate(result.get("values", []), start=1):
            if row and row[0] == client_id:
                return i
    except Exception:
        pass
    return None
