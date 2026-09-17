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
    Swap providers by setting LLM_PROVIDER env var (default: 'gemini').
    """
    provider = os.environ.get("LLM_PROVIDER", "gemini").lower()
    if provider == "gemini":
        return _call_gemini(system_prompt, user_content, model, max_tokens)
    if provider == "anthropic":
        return _call_anthropic(system_prompt, user_content, model, max_tokens)
    raise NotImplementedError(f"LLM provider '{provider}' is not yet supported.")


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
    response = gemini.generate_content(user_content)
    return response.text


def _call_anthropic(
    system_prompt: str,
    user_content: str,
    model: Optional[str],
    max_tokens: int,
) -> str:
    import anthropic  # lazy import — only needed when actually calling

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError("ANTHROPIC_API_KEY is not set.")

    effective_model = model or os.environ.get("CLAUDE_MODEL", "claude-opus-4-5")
    client = anthropic.Anthropic(api_key=api_key)

    logger.debug(f"Calling Claude model={effective_model}, max_tokens={max_tokens}")
    message = client.messages.create(
        model=effective_model,
        max_tokens=max_tokens,
        system=system_prompt,
        messages=[{"role": "user", "content": user_content}],
    )
    return message.content[0].text
