"""
Phase 15 — Client Timeline API
Returns a unified chronological event stream for a single client:
  intake → classification → notes → reminders → queries → appointments
"""
import logging
from flask import Blueprint, jsonify, render_template
from flask_login import current_user

from app.auth.routes import login_required
from app.models.client import Client
from app.models.intake import IntakeResponse
from app.models.note import Note, Reminder
from app.models.query import ClientQuery
from app.models.appointment import Appointment

timeline_bp = Blueprint("timeline", __name__)
logger = logging.getLogger(__name__)


@timeline_bp.route("/clients/<client_id>/timeline")
@login_required
def timeline_page(client_id):
    client = Client.query.get_or_404(client_id)
    from app.models.practitioner import Practitioner
    practitioner = current_user
    return render_template("timeline.html", client=client, practitioner=practitioner)


@timeline_bp.route("/api/clients/<client_id>/timeline")
@login_required
def client_timeline(client_id):
    """
    Returns a merged, sorted event list for the client.
    Each event: { type, title, detail, ts, meta }
    """
    client = Client.query.get_or_404(client_id)
    events = []

    # ── Intake ────────────────────────────────────────────────────────────────
    intakes = IntakeResponse.query.filter_by(client_id=client.id).all()
    for r in intakes:
        cr = r.classification_result or {}
        events.append({
            "type":   "intake",
            "icon":   "📋",
            "title":  "Client onboarded via intake",
            "detail": f"Segment: {cr.get('segment', '—')} · Confidence: {int(cr.get('confidence', 0)*100)}%",
            "ts":     r.created_at.isoformat(),
            "meta":   {"source": r.source},
        })

    # ── Notes ─────────────────────────────────────────────────────────────────
    notes = Note.query.filter_by(client_id=client.id).order_by(Note.created_at).all()
    for n in notes:
        so = n.structured_output or {}
        badge = "🎙" if n.input_type == "voice" else "📝"
        events.append({
            "type":   "note",
            "icon":   badge,
            "title":  f"{'Voice' if n.input_type == 'voice' else 'Typed'} session note",
            "detail": so.get("summary", n.raw_input[:120] + "…"),
            "ts":     n.created_at.isoformat(),
            "meta":   {
                "sentiment":    so.get("sentiment"),
                "action_items": so.get("action_items", []),
                "input_type":   n.input_type,
            },
        })

    # ── Reminders ─────────────────────────────────────────────────────────────
    reminders = Reminder.query.filter_by(client_id=client.id).order_by(Reminder.created_at).all()
    for r in reminders:
        events.append({
            "type":   "reminder",
            "icon":   "⏰",
            "title":  "Reminder set",
            "detail": r.message,
            "ts":     r.created_at.isoformat(),
            "meta":   {
                "due_at":      r.due_at.isoformat(),
                "resolved":    r.resolved_at is not None,
                "resolved_at": r.resolved_at.isoformat() if r.resolved_at else None,
            },
        })

    # ── Queries ───────────────────────────────────────────────────────────────
    queries = ClientQuery.query.filter_by(client_id=client.id).order_by(ClientQuery.created_at).all()
    for q in queries:
        events.append({
            "type":   "query",
            "icon":   "❓" if not q.escalated else "⚠️",
            "title":  "Client query" + (" — escalated" if q.escalated else ""),
            "detail": q.question[:200],
            "ts":     q.created_at.isoformat(),
            "meta":   {
                "escalated":    q.escalated,
                "ai_response":  q.ai_response,
                "practitioner_response": q.practitioner_response,
            },
        })

    # ── Appointments ──────────────────────────────────────────────────────────
    appointments = (
        Appointment.query
        .filter_by(client_id=client.id)
        .order_by(Appointment.scheduled_at)
        .all()
    )
    for a in appointments:
        status_icon = {"scheduled": "📅", "completed": "✅", "cancelled": "❌"}.get(a.status, "📅")
        events.append({
            "type":   "appointment",
            "icon":   status_icon,
            "title":  f"Appointment — {a.status.capitalize()}",
            "detail": f"{a.duration_minutes} min session" + (f" · {a.meet_link}" if a.meet_link else ""),
            "ts":     a.created_at.isoformat(),
            "meta":   {
                "scheduled_at":     a.scheduled_at.isoformat(),
                "duration_minutes": a.duration_minutes,
                "status":           a.status,
                "meet_link":        a.meet_link,
            },
        })

    # Sort all events chronologically
    events.sort(key=lambda e: e["ts"])

    return jsonify({
        "client_id":   client.id,
        "client_name": client.name,
        "events":      events,
        "total":       len(events),
    })
