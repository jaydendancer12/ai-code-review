"""Tests for the reviewer module."""

import pytest
from codereview.reviewer import (
    parse_review_response,
    ReviewResult,
    Severity,
)


class TestParseReviewResponse:
    def test_valid_json(self):
        raw = '''{
            "summary": "Code looks good overall",
            "score": 8,
            "issues": [
                {
                    "severity": "warning",
                    "title": "Missing error handling",
                    "description": "Function doesn't catch exceptions",
                    "suggestion": "Add try/except block"
                }
            ]
        }'''
        result = parse_review_response(raw)
        assert result.score == 8
        assert len(result.issues) == 1
        assert result.issues[0].severity == Severity.WARNING

    def test_json_in_code_block(self):
        raw = '''```json
        {"summary": "OK", "score": 5, "issues": []}
        ```'''
        result = parse_review_response(raw)
        assert result.score == 5

    def test_invalid_json(self):
        raw = "This is not JSON at all"
        result = parse_review_response(raw)
        assert result.score == 0
        assert len(result.issues) == 1

    def test_empty_issues(self):
        raw = '{"summary": "Clean code", "score": 10, "issues": []}'
        result = parse_review_response(raw)
        assert result.score == 10
        assert len(result.issues) == 0

    def test_unknown_severity_defaults_to_info(self):
        raw = '''{
            "summary": "OK",
            "score": 7,
            "issues": [{"severity": "unknown", "title": "Test", "description": "Test"}]
        }'''
        result = parse_review_response(raw)
        assert result.issues[0].severity == Severity.INFO
