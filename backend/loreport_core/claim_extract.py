from __future__ import annotations

import re

from loreport_core.compile_markers import CLAIM_PLACEHOLDER, STATUS_PENDING

_HTTP_METHOD_RE = re.compile(
    r"\b(GET|POST|PUT|PATCH|DELETE|OPTIONS|HEAD)\s+(`?)(/[\w\-./:{}]+)\2",
    re.IGNORECASE,
)
_CURL_RE = re.compile(
    r"curl\b[^\n]*?-X\s+(\w+)\s+[^\n]*?(/[\w\-./:{}]+)",
    re.IGNORECASE,
)
_PATH_IN_BACKTICKS_RE = re.compile(r"`(/[\w\-./:{}]+)`")
_HEADING_RE = re.compile(r"^#{2,4}\s+(.+)$", re.MULTILINE)
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


def _extract_data_model(markdown: str) -> list[str]:
    claims = [f"entity: {name}" for name in _ENTITY_WORD_RE.findall(markdown)]
    for match in _TABLE_ROW_RE.finditer(markdown):
        cell = _normalize_claim(match.group(1))
        if _is_table_separator_cell(cell):
            continue
        if len(cell) <= 48 and re.search(r"\w", cell):
            claims.append(cell)
    claims.extend(_normalize_claim(h) for h in _HEADING_RE.findall(markdown))
    return claims


def _extract_headings(markdown: str) -> list[str]:
    return [_normalize_claim(h) for h in _HEADING_RE.findall(markdown)]


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
        claims = _extract_headings(markdown)
        if aspect_id == "specification":
            claims.extend(_extract_endpoints(markdown))

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
    """Structural: file-existence row, not a testable fact from human doc."""
    normalized = _normalize_claim(claim)
    if not normalized or normalized == CLAIM_PLACEHOLDER:
        return False
    if has_concrete_claim_shape(normalized):
        return False
    # Claim column cites a source file as the subject instead of a behavior/API fact.
    if _SOURCE_FILE_IN_CLAIM_RE.search(normalized):
        return True
    # Very short claim with no URL path, method, or structured prefix.
    if len(normalized.split()) <= 6 and "/" not in normalized:
        return bool(_SOURCE_FILE_IN_CLAIM_RE.search(normalized))
    return False


def is_pending_verification_status(status: str) -> bool:
    normalized = status.strip()
    if not normalized:
        return True
    return normalized in {STATUS_PENDING, CLAIM_PLACEHOLDER}
