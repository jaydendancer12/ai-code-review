"""Core review engine — sends code to LLM and parses response."""

import json
import logging
import requests as req
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum

logger = logging.getLogger(__name__)


class Severity(Enum):
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


REVIEW_PROMPT = """You are an expert code reviewer. Review the following code and respond in EXACTLY this JSON format:

{{
  "summary": "Brief overall assessment in 1-2 sentences",
  "score": <1-10 integer>,
  "issues": [
    {{
      "severity": "critical|warning|info|style",
      "title": "Short issue title",
      "description": "What's wrong and why it matters",
      "file": "filename if known",
      "line": null,
      "suggestion": "How to fix it (code example if applicable)"
    }}
  ]
}}

Review criteria:
- Security vulnerabilities (SQL injection, XSS, secrets in code)
- Bugs and logic errors
- Performance problems
- Error handling gaps
- Code style and readability
- Best practices violations
- Type safety issues
- Missing edge cases

Be specific. Give actionable suggestions. Don't be nice — be helpful.

CODE TO REVIEW:
{code}"""


DIFF_REVIEW_PROMPT = """You are an expert code reviewer reviewing a pull request diff. Review the changes and respond in EXACTLY this JSON format:

{{
  "summary": "Brief overall assessment in 1-2 sentences",
  "score": <1-10 integer>,
  "issues": [
    {{
      "severity": "critical|warning|info|style",
      "title": "Short issue title",
      "description": "What's wrong and why it matters",
      "file": "filename",
      "line": null,
      "suggestion": "How to fix it"
    }}
  ]
}}

Focus on the CHANGES only. Don't review unchanged code.

DIFF:
{code}"""


def _build_session() -> req.Session:
    """Build a reusable requests session with proper SSL and retries."""
    session = req.Session()
    session.verify = True

    adapter = req.adapters.HTTPAdapter(
        max_retries=req.adapters.Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
    )
    session.mount("https://", adapter)
    session.mount("http://", adapter)

    return session


_session = _build_session()


def call_llm(prompt: str, config: Dict[str, Any]) -> str:
    """Call LLM API and return raw response text."""
    api_key = config.get("api_key", "")
    base_url = config.get("base_url", "https://api.openai.com/v1").rstrip("/")
    model = config.get("model", "gpt-3.5-turbo")
    max_tokens = config.get("max_tokens", 2048)
    temperature = config.get("temperature", 0.2)

    headers = {
        "Content-Type": "application/json",
        "User-Agent": "codereview/1.0.0",
    }

    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"

    data = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": temperature,
    }

    try:
        resp = _session.post(
            f"{base_url}/chat/completions",
            json=data,
            headers=headers,
            timeout=60,
            verify=True,
        )
        resp.raise_for_status()
        result = resp.json()
        return result["choices"][0]["message"]["content"]
    except req.exceptions.SSLError as e:
        logger.error(f"SSL verification failed: {e}")
        raise RuntimeError(f"SSL verification failed: {e}")
    except req.exceptions.HTTPError as e:
        logger.error(f"API error {e.response.status_code}: {e.response.text}")
        raise RuntimeError(f"API error {e.response.status_code}: {e.response.text}")
    except req.exceptions.ConnectionError as e:
        logger.error(f"Connection failed: {e}")
        raise RuntimeError(f"Connection failed: {e}")
    except req.exceptions.Timeout:
        logger.error("Request timed out")
        raise RuntimeError("Request timed out after 60 seconds")
    except (KeyError, IndexError, json.JSONDecodeError) as e:
        logger.error(f"Failed to parse API response: {e}")
        raise RuntimeError(f"Failed to parse API response: {e}")


def parse_review_response(raw: str) -> ReviewResult:
    """Parse LLM JSON response into ReviewResult."""
    raw = raw.strip()

    if "```json" in raw:
        raw = raw.split("```json")[1].split("```")[0]
    elif "```" in raw:
        raw = raw.split("```")[1].split("```")[0]

    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("Failed to parse LLM response as JSON")
        return ReviewResult(
            summary="Failed to parse review response. Raw output below.",
            issues=[Issue(
                severity=Severity.INFO,
                title="Raw LLM Output",
                description=raw[:500],
            )],
            score=0,
        )

    issues = []
    for item in data.get("issues", []):
        try:
            severity = Severity(item.get("severity", "info").lower())
        except ValueError:
            severity = Severity.INFO

        issues.append(Issue(
            severity=severity,
            title=item.get("title", "Untitled"),
            description=item.get("description", ""),
            file=item.get("file", ""),
            line=item.get("line"),
            suggestion=item.get("suggestion", ""),
        ))

    return ReviewResult(
        summary=data.get("summary", "No summary provided."),
        issues=issues,
        score=data.get("score", 0),
        files_reviewed=0,
        lines_reviewed=0,
    )


def review_code(code: str, config: Dict[str, Any], is_diff: bool = False) -> ReviewResult:
    """Review code or diff and return structured result."""
    if is_diff:
        prompt = DIFF_REVIEW_PROMPT.format(code=code[:8000])
    else:
        prompt = REVIEW_PROMPT.format(code=code[:8000])

    raw_response = call_llm(prompt, config)
    result = parse_review_response(raw_response)

    line_count = len(code.split("\n"))
    result.lines_reviewed = line_count

    return result
