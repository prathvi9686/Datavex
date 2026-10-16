"""
DataVex Backend — Bytez LLM Client
Calls GPT-4.1 via the Bytez OpenAI-compatible REST API.
"""
import httpx
import json
import logging
from app.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()

TIMEOUT = httpx.Timeout(180.0, connect=15.0)


async def chat_completion(
    messages: list[dict],
    temperature: float = 0.7,
    max_tokens: int = 4096,
    response_format: str | None = None,
) -> str:
    """
    Send a chat completion request to GPT-4.1 via Bytez.

    Args:
        messages: List of {role, content} dicts
        temperature: Sampling temperature
        max_tokens: Max output tokens
        response_format: If "json_object", requests JSON output

    Returns:
        The assistant's text response.
    """
    url = f"{settings.bytez_base_url}/chat/completions"

    headers = {
        "Authorization": f"Bearer {settings.bytez_api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": settings.bytez_model,
        "messages": messages,
        "temperature": temperature,
        "max_completion_tokens": max_tokens,
    }

    if response_format == "json_object":
        payload["response_format"] = {"type": "json_object"}

    logger.info(f"LLM request: model={settings.bytez_model}, msgs={len(messages)}")

    async with httpx.AsyncClient(timeout=TIMEOUT) as client:
        resp = await client.post(url, json=payload, headers=headers)

        if resp.status_code != 200:
            error_text = resp.text
            logger.error(f"LLM API error {resp.status_code}: {error_text}")
            raise Exception(f"Bytez API error {resp.status_code}: {error_text}")

        data = resp.json()

    # OpenAI-compatible response format
    try:
        content = data["choices"][0]["message"]["content"]
        logger.info(f"LLM response: {len(content)} chars")
        return content
    except (KeyError, IndexError) as e:
        logger.error(f"Unexpected LLM response format: {data}")
        raise Exception(f"Unexpected response format: {e}")


async def chat_completion_json(
    messages: list[dict],
    temperature: float = 0.4,
    max_tokens: int = 4096,
) -> dict:
    """
    Chat completion that parses the response as JSON.
    Uses a lower temperature by default for structured output.
    """
    # Add instruction to return valid JSON
    if messages and messages[0]["role"] == "system":
        messages[0]["content"] += "\n\nIMPORTANT: You MUST respond with valid JSON only. No markdown, no code fences, just raw JSON."
    
    raw = await chat_completion(
        messages=messages,
        temperature=temperature,
        max_tokens=max_tokens,
        response_format="json_object",
    )

    # Clean up common LLM JSON issues
    raw = raw.strip()
    if raw.startswith("```json"):
        raw = raw[7:]
    if raw.startswith("```"):
        raw = raw[3:]
    if raw.endswith("```"):
        raw = raw[:-3]
    raw = raw.strip()

    try:
        return json.loads(raw)
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse LLM JSON: {e}\nRaw: {raw[:500]}")
        # Try to extract JSON from the response
        start = raw.find("{")
        end = raw.rfind("}") + 1
        if start >= 0 and end > start:
            try:
                return json.loads(raw[start:end])
            except json.JSONDecodeError:
                pass
        raise Exception(f"LLM returned invalid JSON: {e}")
