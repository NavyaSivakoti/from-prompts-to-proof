"""The only module that calls the model: one OpenAI answer per question."""

import logging
import os

from openai import AsyncOpenAI, OpenAIError

from demo import config

logger = logging.getLogger(__name__)


class ModelError(Exception):
    """A useful error message that is safe to show in the browser."""


def api_key_configured() -> bool:
    value = os.getenv("OPENAI_API_KEY", "").strip()
    return bool(value) and value not in {"your-key-here", "sk-your-key-here"}


def _client() -> AsyncOpenAI:
    if not api_key_configured():
        raise ModelError("OpenAI API key is not configured.")
    return AsyncOpenAI(
        api_key=os.environ["OPENAI_API_KEY"].strip(),
        timeout=config.REQUEST_TIMEOUT_SECONDS,
        max_retries=0,  # One request per question, with no hidden retries.
    )


def _safe_error(exc: OpenAIError) -> ModelError:
    # Never log raw exception text: provider errors can include credential fragments.
    status = getattr(exc, "status_code", None)
    logger.warning("OpenAI request failed: type=%s status=%s", type(exc).__name__, status)
    if status == 401:
        detail = "OpenAI authentication failed. Check your local API key."
    elif status == 429:
        detail = "OpenAI request failed (429): rate limit or API quota exceeded."
    elif status == 404:
        detail = "OpenAI request failed (404): the configured model is unavailable."
    elif status:
        detail = f"OpenAI request failed (HTTP {status}). Please try again."
    else:
        detail = "OpenAI connection failed or timed out. Check your connection and try again."
    return ModelError(detail)


async def generate_response(question: str, context: str, prompt: str, history: list[dict] | None = None) -> str:
    # This string is also shown in View Context: we never add unseen company facts.
    company_message = "Company information for this question:\n" + (
        context or "No matching company information was found for this question."
    )
    try:
        async with _client() as client:
            completion = await client.chat.completions.create(
                model=config.MODEL,
                temperature=config.TEMPERATURE,
                max_completion_tokens=config.MAX_COMPLETION_TOKENS,
                store=False,
                messages=[
                    {"role": "system", "content": prompt},
                    {"role": "system", "content": company_message},
                    *(history or [])[-config.MAX_HISTORY_MESSAGES:],
                    {"role": "user", "content": question},
                ],
            )
    except OpenAIError as exc:
        raise _safe_error(exc) from None
    if not completion.choices or not completion.choices[0].message.content:
        raise ModelError("OpenAI returned no answer. Please try again.")
    if completion.choices[0].finish_reason == "length":
        raise ModelError("OpenAI response reached the token limit. Increase the configured limit and retry.")
    return completion.choices[0].message.content
