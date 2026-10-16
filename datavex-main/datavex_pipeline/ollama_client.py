"""
DataVex — Ollama Client
Single LLM interface for all DataVex agents.

Priority:
  1. Delegates to datavex_pipeline/config.py's llm_call_with_retry when available
     (uses BYTEZ_BASE_URL = http://100.109.131.90:11434/v1 from backend/.env)
  2. Falls back to direct Ollama /api/generate POST if config.py is unavailable
  3. Returns None / "LLM unavailable" on any failure

All agents use this module — never call Ollama directly.
"""
import json
import logging
import os
import re as _re

logger = logging.getLogger("datavex.ollama")

# ── Detect remote Ollama base from env ──────────────────────────
def _ollama_base() -> str:
    """
    Resolve the Ollama base URL.
    Reads BYTEZ_BASE_URL from backend/.env or env var.
    Strips /v1 suffix to get the native Ollama endpoint.
    """
    # Try backend/.env first
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for env_candidate in [
        os.path.join(root, "backend", ".env"),
        os.path.join(root, ".env"),
    ]:
        if os.path.exists(env_candidate):
            with open(env_candidate) as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("BYTEZ_BASE_URL="):
                        url = line.split("=", 1)[1].strip()
                        return url.removesuffix("/v1")
    # Env var fallback
    url = os.getenv("OLLAMA_BASE", os.getenv("BYTEZ_BASE_URL", "http://localhost:11434"))
    return url.removesuffix("/v1")


def _ollama_model() -> str:
    """Read model name from backend/.env or env."""
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for env_candidate in [
        os.path.join(root, "backend", ".env"),
        os.path.join(root, ".env"),
    ]:
        if os.path.exists(env_candidate):
            with open(env_candidate) as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("BYTEZ_MODEL="):
                        return line.split("=", 1)[1].strip()
    return os.getenv("BYTEZ_MODEL", "llama3.1:8b")


_DEFAULT_BASE  = _ollama_base()
_DEFAULT_MODEL = _ollama_model()


# ── Config.py delegation (preferred path) ────────────────────────

def _config_call(prompt: str, system: str = "", expect_json: bool = False):
    """
    Attempt to delegate to config.py's llm_call_with_retry.
    Returns dict (if expect_json) or string, or None on failure.
    """
    try:
        import sys
        pipeline_dir = os.path.dirname(os.path.abspath(__file__))
        if pipeline_dir not in sys.path:
            sys.path.insert(0, pipeline_dir)
        from config import llm_call_with_retry, OFFLINE_MODE
        if OFFLINE_MODE:
            return None
        result = llm_call_with_retry(prompt=prompt, system=system)
        if expect_json:
            return result if isinstance(result, dict) else None
        # Return as string if text expected
        if isinstance(result, dict):
            return result.get("response") or result.get("text") or json.dumps(result)
        return str(result) if result else None
    except Exception as e:
        logger.debug("config.py delegation failed: %s", e)
        return None


# ── Direct Ollama /api/generate (fallback) ───────────────────────

def _direct_call(
    prompt: str,
    system: str = "",
    model: str = _DEFAULT_MODEL,
    timeout: int = 30,
    expect_json: bool = False,
):
    """
    Direct POST to Ollama /api/generate. Used when config.py unavailable.
    """
    import urllib.request
    import urllib.error

    payload = {
        "model":   model,
        "prompt":  prompt,
        "stream":  False,
        "options": {"temperature": 0.3, "num_predict": 512},
    }
    if system:
        payload["system"] = system

    try:
        data = json.dumps(payload).encode()
        req  = urllib.request.Request(
            f"{_DEFAULT_BASE}/api/generate",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read())
            text = body.get("response", "").strip()

        if not text:
            return None
        if expect_json:
            return _extract_json(text)
        return text

    except urllib.error.URLError:
        logger.warning("Ollama unavailable at %s", _DEFAULT_BASE)
        return None
    except Exception as e:
        logger.warning("Ollama direct call failed: %s", e)
        return None


# ── Public API ───────────────────────────────────────────────────

def ollama_call(
    prompt: str,
    system: str = "",
    model: str = _DEFAULT_MODEL,
    timeout: int = 30,
    expect_json: bool = False,
):
    """
    Blocking Ollama call.
    Primary: direct /api/generate to remote host (confirmed reachable).
    Fallback: config.py llm_call_with_retry (if available & not OFFLINE).
    Returns None on total failure.
    """
    # Direct path first (remote Ollama /api/generate)
    result = _direct_call(prompt, system, model, timeout, expect_json)
    if result is not None:
        return result

    # Config.py delegation fallback
    return _config_call(prompt, system, expect_json)


def ollama_embed(text: str, model: str = "nomic-embed-text") -> list[float] | None:
    """
    Get embedding vector.
    Tries Ollama /api/embeddings on the remote host.
    """
    import urllib.request
    import urllib.error

    payload = {"model": model, "prompt": text}
    try:
        data = json.dumps(payload).encode()
        req  = urllib.request.Request(
            f"{_DEFAULT_BASE}/api/embeddings",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            body = json.loads(resp.read())
            return body.get("embedding")
    except Exception as e:
        logger.debug("Ollama embed failed (%s): %s", _DEFAULT_BASE, e)
        return None


def ollama_available() -> bool:
    """Ping the remote Ollama host."""
    import urllib.request
    try:
        urllib.request.urlopen(f"{_DEFAULT_BASE}/api/tags", timeout=4)
        return True
    except Exception:
        return False


# ── JSON extraction helper ────────────────────────────────────────

def _extract_json(text: str):
    """Parse JSON from LLM response — handles markdown fences."""
    fence = _re.search(r"```(?:json)?\s*([\s\S]+?)\s*```", text)
    if fence:
        text = fence.group(1)

    brace_start = text.find("{")
    brace_end   = text.rfind("}") + 1
    if brace_start != -1 and brace_end > brace_start:
        try:
            return json.loads(text[brace_start:brace_end])
        except json.JSONDecodeError:
            pass

    arr_start = text.find("[")
    arr_end   = text.rfind("]") + 1
    if arr_start != -1 and arr_end > arr_start:
        try:
            return json.loads(text[arr_start:arr_end])
        except json.JSONDecodeError:
            pass

    logger.warning("Could not parse JSON from LLM response: %.80s", text)
    return None
