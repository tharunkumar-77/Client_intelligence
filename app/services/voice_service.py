"""
Phase 4 — Voice Input Service
Uses Gemini's native audio understanding to transcribe a recorded audio blob,
then passes the transcript through the existing note pipeline.
"""
import io
import logging
import os
import tempfile
from typing import Optional

logger = logging.getLogger(__name__)

_TRANSCRIPTION_PROMPT = """
You are transcribing an audio recording made by a financial adviser during or after a client session.

Your task:
1. Produce an accurate, clean transcript of the speech.
2. Fix obvious filler words (um, uh) silently unless they signal hesitation worth noting.
3. If the audio is inaudible or empty, return exactly: [No speech detected]

Return ONLY the plain-text transcript. No JSON, no headers, no explanation.
""".strip()


def transcribe_audio(audio_bytes: bytes, mime_type: str = "audio/webm") -> Optional[str]:
    """
    Upload audio bytes to the Gemini Files API, transcribe, delete the file.
    Returns the transcript string, or None on failure.
    """
    import google.generativeai as genai

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not set.")

    genai.configure(api_key=api_key)

    # Write to a named temp file — Gemini Files API needs a file path or file-like
    suffix = _mime_to_ext(mime_type)
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as tmp:
        tmp.write(audio_bytes)
        tmp_path = tmp.name

    uploaded = None
    try:
        logger.debug("Uploading %d bytes of audio (%s) to Gemini Files API", len(audio_bytes), mime_type)
        uploaded = genai.upload_file(path=tmp_path, mime_type=mime_type)

        model = genai.GenerativeModel(
            model_name=os.environ.get("GEMINI_MODEL", "gemini-1.5-pro"),
            system_instruction=_TRANSCRIPTION_PROMPT,
        )
        response = model.generate_content([uploaded])
        transcript = response.text.strip()

        if transcript == "[No speech detected]" or not transcript:
            logger.info("Gemini reported no speech in audio")
            return None

        logger.info("Transcription complete: %d chars", len(transcript))
        return transcript

    finally:
        # Always clean up the temp file and the uploaded Gemini file
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        if uploaded:
            try:
                genai.delete_file(uploaded.name)
            except Exception:
                pass


def _mime_to_ext(mime_type: str) -> str:
    mapping = {
        "audio/webm": ".webm",
        "audio/ogg": ".ogg",
        "audio/mp4": ".mp4",
        "audio/mpeg": ".mp3",
        "audio/wav": ".wav",
    }
    return mapping.get(mime_type, ".webm")
