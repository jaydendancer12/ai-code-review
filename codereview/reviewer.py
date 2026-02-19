"""Core review engine — sends code to LLM and parses structured response."""

import json
import logging
import hashlib
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

import requests as req
from requests.adapters import HTTPAdapter, Retry

logger = logging.getLogger(__name__)


class Severity(Enum):
    """Issue severity levels ordered by importance."""
    CRITICAL = "critical"
    WARNING = "warning"
    INFO = "info"
    STYLE = "style"


@dataclass
class Issue:
    """A single code review finding."""
    severity: Severity
    title: str
    description: str
    file: str = ""
    line: Optional[int] = None
    suggestion: str = ""


@dataclass
class ReviewResult:
    """Complete review output."""
    summary: str
    issues: List[Issue] = field(default_factory=list)
    score: int = 0
    files_reviewed: int = 0
    lines_reviewed: int = 0


REVIEW_PROMPT: str = """You are an expert code reviewer. Review ONLY the code below.

RULES:
- Only report issues you can SEE in the actual code provided
- Do NOT speculate about code that might exist elsewhere
- Do NOT flag standard practices (env vars for config, etc.) as issues
- Every issue MUST reference a specific line or pattern in the provided code
- If the code is clean, say so — do not invent problems

Respond in EXACTLY this JSON format:

{{
  "summary": "Brief overall assessment in 1-2 sentences",
  "score": <1-10 integer>,
  "issues": [
    {{
      "severity": "critical|warning|info|style",
      "title": "Short issue title",
      "description": "What's wrong and why — reference the specific code",
      "file": "filename",
      "line": null,
      "suggestion": "Concrete fix with code example"
    }}
  ]
}}

Severity guide:
- critical: Security vulnerabilities, data loss, crashes (must be PROVEN in code)
- warning: Bugs, missing error handling, race conditions (must be visible)
- info: Performance improvements, better patterns
- style: Naming, formatting, docstrings

CODE TO REVIEW:
{code}"""


DIFF_REVIEW_PROMPT: str = """You are an expert code reviewer reviewing a pull request diff.

RULES:
- Only review the CHANGED lines
- Only report issues you can SEE in the diff
- Do NOT speculate about code outside the diff
- Every issue MUST point to a specific change
- If changes are clean, say so

Respond in EXACTLY this JSON format:

{{
  "summary": "Brief overall assessment in 1-2 sentences",
  "score": <1-10 integer>,
  "issues": [
    {{
      "severity": "critical|warning|info|style",
      "title": "Short issue title",
      "description": "What's wrong — reference the specific change",
      "file": "filename",
      "line": null,
      "suggestion": "Concrete fix"
    }}
  ]
}}

DIFF:
{code}"""


# ─── HTTP Session ───

def _build_session() -> req.Session:
    """Build a reusable HTTP session with SSL verification and retries."""
    session: req.Session = req.Session()
    session.verify = True

    retry_strategy: Retry = Retry(
        total=3,
        backoff_factor=1.0,
        status_forcelist=[429, 500, 502, 503, 504],
        allowed_methods=["POST"],
    )

    adapter: HTTPAdapter = HTTPAdapter(max_retries=retry_strategy)
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    return session


_session: req.Session = _build_session()


# ─── Response Cache ───

_response_cache: Dict[str, str] = {}
MAX_CACHE_SIZE: int = 50


def _get_cache_key(prompt: str, model: str) -> str:
    """Generate deterministic cache key for prompt + model pair."""
    raw: str = f"{model}:{prompt}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


# ─── LLM API Call ───

def _validate_api_config(config: Dict[str, Any]) -> Tuple[str, str, str]:
    """Extract and validate API configuration."""
    base_url: str = config.get("base_url", "https://api.openai.com/v1").rstrip("/")
    model: str = config.get("model", "gpt-3.5-turbo")
    api_key: str = config.get("api_key", "")

    if not base_url:
        raise RuntimeError("No API base URL configured")
    if not model:
        raise RuntimeError("No model configured")

    return base_url, model, api_key


def _build_headers(api_key: str) -> Dict[str, str]:
    """Build HTTP headers for the API request."""
    headers: Dict[str, str] = {
        "Content-Type": "application/json",
        "User-Agent": "codereview/1.0.0",
    }
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    return headers


def _build_payload(prompt: str, model: str, config: Dict[str, Any]) -> Dict[str, Any]:
    """Build the API request payload."""
    return {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": int(config.get("max_tokens", 2048)),
        "temperature": float(config.get("temperature", 0.2)),
    }


def _extract_response_text(data: Dict[str, Any]) -> str:
    """Extract message content from API response."""
    try:
        choices: List[Dict] = data["choices"]
        if not choices:
            raise RuntimeError("API returned empty choices array")
        return choices[0]["message"]["content"]
    except (KeyError, IndexError, TypeError) as e:
        raise RuntimeError(f"Unexpected API response structure: {e}")


def call_llm(prompt: str, config: Dict[str, Any]) -> str:
    """Call LLM API with caching, retries, and SSL verification."""
    base_url, model, api_key = _validate_api_config(config)

    cache_key: str = _get_cache_key(prompt, model)
    if cache_key in _response_cache:
        logger.debug("Cache hit")
        return _response_cache[cache_key]

    headers: Dict[str, str] = _build_headers(api_key)
    payload: Dict[str, Any] = _build_payload(prompt, model, config)

    try:
        resp: req.Response = _session.post(
            f"{base_url}/chat/completions",
            json=payload,
            headers=headers,
            timeout=60,
            verify=True,
        )
        resp.raise_for_status()

        data: Dict[str, Any] = resp.json()
        content: str = _extract_response_text(data)

        if len(_response_cache) >= MAX_CACHE_SIZE:
            oldest_key: str = next(iter(_response_cache))
            del _response_cache[oldest_key]
        _response_cache[cache_key] = content

        return content

    except req.exceptions.SSLError as e:
        logger.error(f"SSL verification failed: {e}")
        raise RuntimeError(f"SSL verification failed: {e}")
    except req.exceptions.HTTPError as e:
        status: int = e.response.status_code if e.response else 0
        body: str = e.response.text if e.response else "no response"
        logger.error(f"API error {status}: {body}")
        raise RuntimeError(f"API error {status}: {body}")
    except req.exceptions.ConnectionError as e:
        logger.error(f"Connection failed: {e}")
        raise RuntimeError(f"Connection failed: {e}")
    except req.exceptions.Timeout:
        logger.error("Request timed out")
        raise RuntimeError("Request timed out after 60 seconds")
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in response: {e}")
        raise RuntimeError(f"API returned invalid JSON: {e}")


# ─── Response Parsing ───

def _extract_json_from_response(raw: str) -> str:
    """Extract JSON from potentially markdown-wrapped response."""
    raw = raw.strip()
    if "```json" in raw:
        return raw.split("```json")[1].split("```")[0].strip()
    if "```" in raw:
        return raw.split("```")[1].split("```")[0].strip()
    return raw


def _parse_severity(value: str) -> Severity:
    """Parse severity string into enum, defaulting to INFO."""
    try:
        return Severity(value.lower().strip())
    except (ValueError, AttributeError):
        return Severity.INFO


def _parse_issue(item: Dict[str, Any]) -> Issue:
    """Parse a single issue dict into an Issue dataclass."""
    return Issue(
        severity=_parse_severity(item.get("severity", "info")),
        title=str(item.get("title", "Untitled")).strip(),
        description=str(item.get("description", "")).strip(),
        file=str(item.get("file", "")).strip(),
        line=item.get("line") if isinstance(item.get("line"), int) else None,
        suggestion=str(item.get("suggestion", "")).strip(),
    )


def parse_review_response(raw: str) -> ReviewResult:
    """Parse LLM JSON response into structured ReviewResult."""
    cleaned: str = _extract_json_from_response(raw)

    try:
        data: Dict[str, Any] = json.loads(cleaned)
    except json.JSONDecodeError:
        logger.warning("Failed to parse LLM response as JSON")
        return ReviewResult(
            summary="Failed to parse review response.",
            issues=[Issue(
                severity=Severity.INFO,
                title="Raw LLM Output",
                description=raw[:500],
            )],
            score=0,
        )

    issues: List[Issue] = [
        _parse_issue(item) for item in data.get("issues", [])
        if isinstance(item, dict)
    ]

    score_raw: Any = data.get("score", 0)
    score: int = max(0, min(10, int(score_raw))) if isinstance(score_raw, (int, float)) else 0

    return ReviewResult(
        summary=str(data.get("summary", "No summary provided.")).strip(),
        issues=issues,
        score=score,
    )


# ─── Main Entry Point ───

def _validate_code_input(code: str) -> str:
    """Validate code input is not empty."""
    if not code or not code.strip():
        raise ValueError("No code provided for review")
    return code.strip()


def review_code(code: str, config: Dict[str, Any], is_diff: bool = False) -> ReviewResult:
    """Review code or diff and return structured findings."""
    clean_code: str = _validate_code_input(code)

    truncated: str = clean_code[:8000]
    if is_diff:
        prompt: str = DIFF_REVIEW_PROMPT.format(code=truncated)
    else:
        prompt = REVIEW_PROMPT.format(code=truncated)

    raw_response: str = call_llm(prompt, config)
    result: ReviewResult = parse_review_response(raw_response)
    result.lines_reviewed = len(clean_code.split("\n"))

    return result
