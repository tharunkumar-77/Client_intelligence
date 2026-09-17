import logging
from typing import Any, Dict, Optional

from app.extensions import db
from app.models.audit import AuditLog

logger = logging.getLogger(__name__)


def log_event(
    action: str,
    actor: str,
    practitioner_id: Optional[str] = None,
    client_id: Optional[str] = None,
    payload: Optional[Dict[str, Any]] = None,
) -> AuditLog:
    """
    Write an immutable audit log entry.
    actor: 'ai' | 'practitioner' | 'system'
    """
    try:
        entry = AuditLog(
            practitioner_id=practitioner_id,
            client_id=client_id,
            action=action,
            actor=actor,
            payload=payload or {},
        )
        db.session.add(entry)
        db.session.commit()
        return entry
    except Exception as exc:
        logger.exception(f"Failed to write audit log for action '{action}': {exc}")
        db.session.rollback()
        raise
