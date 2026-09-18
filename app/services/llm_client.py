import os
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def call_llm(
    system_prompt: str,
    user_content: str,
    model: Optional[str] = None,
    max_tokens: int = 1024,
) -> str:
    """
    Call the configured LLM provider and return the raw text response.
    """
    return _call_gemini(system_prompt, user_content, model, max_tokens)


def _call_gemini(
    system_prompt: str,
    user_content: str,
    model: Optional[str],
    max_tokens: int,
) -> str:
    import google.generativeai as genai  # lazy import

    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not set.")

    effective_model = model or os.environ.get("GEMINI_MODEL", "gemini-1.5-pro")
    genai.configure(api_key=api_key)

    generation_config = genai.types.GenerationConfig(max_output_tokens=max_tokens)
    gemini = genai.GenerativeModel(
        model_name=effective_model,
        system_instruction=system_prompt,
        generation_config=generation_config,
    )

    logger.debug(f"Calling Gemini model={effective_model}, max_tokens={max_tokens}")
    import time
    for attempt in range(2):
        try:
            response = gemini.generate_content(
                user_content,
                request_options={"timeout": 30.0}
            )
            return response.text
        except Exception as e:
            if attempt == 1:
                raise
            logger.warning("LLM call failed (attempt %d): %s", attempt + 1, e)
            time.sleep(1)


