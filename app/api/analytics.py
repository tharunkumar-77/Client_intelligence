"""
Phase 11 — Analytics & Insights API
Provides aggregated, chart-ready data for the analytics dashboard.
"""
import logging
from collections import defaultdict
from datetime import datetime, timezone, timedelta

from flask import Blueprint, jsonify, render_template
from flask_login import current_user

from app.auth.routes import login_required
from app.extensions import db
from app.models.client import Client
from app.models.note import Note, Reminder
from app.models.practitioner import Practitioner

analytics_bp = Blueprint("analytics", __name__)
logger = logging.getLogger(__name__)


@analytics_bp.route("/analytics")
@login_required
def analytics_page():
    practitioner = current_user
    return render_template("analytics.html", practitioner=practitioner)


@analytics_bp.route("/api/analytics/overview")
@login_required
def analytics_overview():
    """
    Returns all chart data in one JSON payload:
     - clients_by_segment
     - clients_by_risk
     - clients_by_urgency
     - sentiment_distribution
     - notes_over_time  (last 30 days)
     - clients_over_time (last 30 days)
     - avg_triage_score_by_segment
    """
    practitioner = current_user
    if not practitioner:
        return jsonify({"error": "No practitioner"}), 500

    pid = practitioner.id

    # ── All clients ────────────────────────────────────────────────────────────
    clients = Client.query.filter_by(practitioner_id=pid).all()

    # Segment breakdown
    seg_counts: dict = defaultdict(int)
    for c in clients:
        label = c.segment.name if c.segment else "Unclassified"
        seg_counts[label] += 1

    # Risk breakdown
    risk_counts: dict = defaultdict(int)
    for c in clients:
        risk_counts[c.risk_level or "Unknown"] += 1

    # Urgency breakdown
    urgency_counts: dict = defaultdict(int)
    for c in clients:
        urgency_counts[c.urgency or "Unknown"] += 1

    # ── Notes ──────────────────────────────────────────────────────────────────
    notes = (
        Note.query
        .join(Client, Note.client_id == Client.id)
        .filter(Client.practitioner_id == pid)
        .all()
    )

    # Sentiment distribution
    sentiment_counts: dict = defaultdict(int)
    for n in notes:
        so = n.structured_output or {}
        sentiment_counts[so.get("sentiment", "Unknown")] += 1

    # Notes over last 30 days (daily counts)
    today = datetime.now(timezone.utc).date()
    days_30 = {(today - timedelta(days=i)).isoformat(): 0 for i in range(29, -1, -1)}
    for n in notes:
        d = n.created_at.date().isoformat()
        if d in days_30:
            days_30[d] += 1

    # Clients registered over last 30 days
    client_days: dict = {(today - timedelta(days=i)).isoformat(): 0 for i in range(29, -1, -1)}
    for c in clients:
        d = c.created_at.date().isoformat()
        if d in client_days:
            client_days[d] += 1

    # ── Triage scores by segment ───────────────────────────────────────────────
    # triage_score is stored in client.attributes as "triage_score" (Phase 5)
    seg_scores: dict = defaultdict(list)
    for c in clients:
        attrs = c.attributes or {}
        score = attrs.get("triage_score")
        if score is not None:
            try:
                seg_scores[c.segment.name if c.segment else "Unclassified"].append(float(score))
            except (TypeError, ValueError):
                pass

    avg_triage = {
        seg: round(sum(scores) / len(scores), 2)
        for seg, scores in seg_scores.items() if scores
    }

    # ── Reminders stats ────────────────────────────────────────────────────────
    now = datetime.now(timezone.utc)
    reminders = (
        Reminder.query
        .join(Client, Reminder.client_id == Client.id)
        .filter(Client.practitioner_id == pid)
        .all()
    )
    total_reminders = len(reminders)
    overdue = sum(1 for r in reminders if r.resolved_at is None and r.due_at < now)
    resolved = sum(1 for r in reminders if r.resolved_at is not None)

    return jsonify({
        "total_clients": len(clients),
        "total_notes": len(notes),
        "clients_by_segment": dict(seg_counts),
        "clients_by_risk": dict(risk_counts),
        "clients_by_urgency": dict(urgency_counts),
        "sentiment_distribution": dict(sentiment_counts),
        "notes_over_time": days_30,
        "clients_over_time": client_days,
        "avg_triage_score_by_segment": avg_triage,
        "reminders": {
            "total": total_reminders,
            "overdue": overdue,
            "resolved": resolved,
        },
    })
