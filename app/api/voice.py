"""Phase 4 — Voice Note API routes"""
import logging

from flask import Blueprint, jsonify, request
from flask_login import current_user

from app.extensions import db, limiter, get_client_for_user
from app.models.client import Client
from app.services.audit_service import log_event
from app.services.note_service import process_note
from app.services.voice_service import transcribe_audio

voice_bp = Blueprint("voice", __name__)
logger = logging.getLogger(__name__)


@voice_bp.route("/clients/<client_id>/notes/voice", methods=["POST"])
@limiter.limit("5 per minute")
def voice_note(client_id):
    """
    Accepts a multipart/form-data audio file ('audio' field) or
    raw audio bytes with Content-Type set to audio/webm (etc.).

    Pipeline:
      audio bytes → Gemini transcription → note_service.process_note
    Returns the same NoteResult JSON as the typed notes endpoint.
    """
    client = get_client_for_user(client_id)
    practitioner = current_user
    if not practitioner:
        return jsonify({"error": "No practitioner configured."}), 500

    # ── Accept multipart OR raw body ──────────────────────────────────────────
    if request.files.get("audio"):
        f = request.files["audio"]
        audio_bytes = f.read()
        mime_type = f.mimetype or "audio/webm"
    elif request.data:
        audio_bytes = request.data
        mime_type = request.content_type or "audio/webm"
    else:
        return jsonify({"error": "No audio data received."}), 400

    if len(audio_bytes) < 512:
        return jsonify({"error": "Audio clip too short or empty."}), 400

    # ── Transcribe ────────────────────────────────────────────────────────────
    try:
        transcript = transcribe_audio(audio_bytes, mime_type)
    except Exception as exc:
        logger.exception("Voice transcription failed")
        return jsonify({"error": f"Transcription failed: {exc}"}), 500

    if not transcript:
        return jsonify({"error": "No speech detected in the recording."}), 422

    # ── Run through the standard note pipeline ────────────────────────────────
    result = process_note(client, transcript, practitioner.id)

    # Mark this note as voice input
    if result.success:
        from app.models.note import Note
        note = Note.query.get(result.note_id)
        if note:
            note.input_type = "voice"
            db.session.commit()

    log_event(
        action="voice_note_processed",
        actor="ai",
        practitioner_id=practitioner.id,
        client_id=client.id,
        payload={
            "note_id": result.note_id,
            "transcript_chars": len(transcript),
            "sentiment": result.sentiment,
            "success": result.success,
        },
    )

    payload = result.to_dict()
    payload["transcript"] = transcript  # include transcript in response
    return jsonify(payload), 200 if result.success else 500
