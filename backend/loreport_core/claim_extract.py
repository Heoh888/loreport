from __future__ import annotations

import re

from loreport_core.compile_markers import (
    CLAIM_PLACEHOLDER,
    STATUS_DRIFT,
    STATUS_MATCH,
    STATUS_MISSING_CODE,
    STATUS_MISSING_DOC,
    STATUS_PENDING,
)

_HTTP_METHOD_RE = re.compile(
    r"\b(GET|POST|PUT|PATCH|DELETE|OPTIONS|HEAD)\s+(`?)(/[\w\-./:{}]+)\2",
    re.IGNORECASE,
)
_CURL_RE = re.compile(
    r"curl\b[^\n]*?-X\s+(\w+)\s+[^\n]*?(/[\w\-./:{}]+)",
    re.IGNORECASE,
)
_PATH_IN_BACKTICKS_RE = re.compile(r"`(/[\w\-./:{}]+)`")
# Technical tokens — same in code/config regardless of doc human language.
_QUEUE_RE = re.compile(
    r"(?:queue|exchange|routing[_\s-]?key|event|topic)[\s:]+[`\"']?([\w.-]+)",
    re.IGNORECASE,
)
_TABLE_ROW_RE = re.compile(r"^\|\s*([^|]+?)\s*\|", re.MULTILINE)
_ENTITY_WORD_RE = re.compile(
    r"\b(?:entity|table|model)\s+[`\"']?([\w.-]+)",
    re.IGNORECASE,
)
_SOURCE_FILE_IN_CLAIM_RE = re.compile(
    r"[/\\]?[\w./-]+\.(py|ts|tsx|go|rs|java|rb|php|kt)\b",
    re.IGNORECASE,
)
_TECHNICAL_TOKEN_RE = re.compile(
    r"[`/\\:=@]|\b\d{2,}\b|\b(GET|POST|PUT|PATCH|DELETE|OPTIONS|HEAD)\b",
    re.IGNORECASE,
)
_LINE_REF_RE = re.compile(r":\d+\b")


def _normalize_claim(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip())


def _is_table_separator_cell(cell: str) -> bool:
    stripped = cell.strip().lower()
    if not stripped:
        return True
    if set(stripped) <= set("-: "):
        return True
    return stripped in {"field", "type", "name", "claim", "status"}


def _dedupe_claims(claims: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for claim in claims:
        normalized = _normalize_claim(claim)
        if not normalized:
            continue
        key = normalized.lower()
        if key in seen:
            continue
        seen.add(key)
        result.append(normalized)
    return result


def _extract_endpoints(markdown: str) -> list[str]:
    claims: list[str] = []
    for match in _HTTP_METHOD_RE.finditer(markdown):
        claims.append(f"{match.group(1).upper()} {match.group(3)}")
    for match in _CURL_RE.finditer(markdown):
        claims.append(f"{match.group(1).upper()} {match.group(2)}")
    for path in _PATH_IN_BACKTICKS_RE.findall(markdown):
        if path.startswith("/"):
            claims.append(path)
    return claims


def _extract_messaging(markdown: str) -> list[str]:
    claims = [f"queue/event: {name}" for name in _QUEUE_RE.findall(markdown)]
    claims.extend(_extract_endpoints(markdown))
    return claims


def _extract_concrete_claims(markdown: str) -> list[str]:
    """Structural facts identifiable without LLM — not section titles."""
    claims: list[str] = []
    claims.extend(_extract_endpoints(markdown))
    claims.extend(f"queue/event: {name}" for name in _QUEUE_RE.findall(markdown))
    claims.extend(f"entity: {name}" for name in _ENTITY_WORD_RE.findall(markdown))
    return claims


def _extract_data_model(markdown: str) -> list[str]:
    claims = [f"entity: {name}" for name in _ENTITY_WORD_RE.findall(markdown)]
    for match in _TABLE_ROW_RE.finditer(markdown):
        cell = _normalize_claim(match.group(1))
        if _is_table_separator_cell(cell):
            continue
        if len(cell) <= 48 and re.search(r"\w", cell):
            claims.append(cell)
    return claims


def extract_claims_for_aspect(markdown: str, aspect_id: str) -> list[str]:
    if not markdown.strip():
        return []

    if aspect_id == "api":
        claims = _extract_endpoints(markdown)
    elif aspect_id == "messaging":
        claims = _extract_messaging(markdown)
    elif aspect_id == "data-model":
        claims = _extract_data_model(markdown)
    else:
        claims = _extract_concrete_claims(markdown)

    return _dedupe_claims(claims)


def has_concrete_claim_shape(claim: str) -> bool:
    if re.search(r"\b(GET|POST|PUT|PATCH|DELETE|OPTIONS|HEAD)\s+/", claim, re.I):
        return True
    if claim.startswith(("queue/event:", "entity:")):
        return True
    if claim.startswith("/") and len(claim) > 1:
        return True
    if _LINE_REF_RE.search(claim):
        return True
    return False


def is_shallow_verification_claim(claim: str) -> bool:
    """Structural: section title or navigation label, not a testable fact."""
    normalized = _normalize_claim(claim)
    if not normalized or normalized == CLAIM_PLACEHOLDER:
        return False
    if has_concrete_claim_shape(normalized):
        return False
    if _SOURCE_FILE_IN_CLAIM_RE.search(normalized):
        return True
    if _TECHNICAL_TOKEN_RE.search(normalized):
        return False
    return True


def is_pending_verification_status(status: str) -> bool:
    normalized = status.strip()
    if not normalized:
        return True
    return normalized in {STATUS_PENDING, CLAIM_PLACEHOLDER}


def is_match_verification_status(status: str) -> bool:
    normalized = status.strip().lower()
    if is_pending_verification_status(status):
        return False
    if normalized == STATUS_MATCH or normalized.startswith(f"{STATUS_MATCH}:"):
        return True
    return normalized in {"ok", "match", "aligned"}


def drift_severity_for_status(status: str) -> str | None:
    normalized = status.strip().lower()
    if is_pending_verification_status(status) or is_match_verification_status(status):
        return None
    if (
        normalized == STATUS_DRIFT
        or normalized.startswith(f"{STATUS_DRIFT}:")
        or normalized == STATUS_MISSING_CODE
        or normalized.startswith(f"{STATUS_MISSING_CODE}:")
    ):
        return "critical"
    if (
        normalized == STATUS_MISSING_DOC
        or normalized.startswith(f"{STATUS_MISSING_DOC}:")
    ):
        return "warning"
    if normalized:
        return "warning"
    return None
