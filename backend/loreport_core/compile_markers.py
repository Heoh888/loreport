from __future__ import annotations

# Language-agnostic protocol between Python pre-compile and agent.
# Visible headings use stable slugs; agent localizes to LOREPORT_LANGUAGE on edit.

HUMAN_DOC_BEGIN = "<!-- loreport:human-doc:do-not-edit -->"
HUMAN_DOC_END = "<!-- /loreport:human-doc -->"

VERIFICATION_BEGIN = "<!-- loreport:verification:pending -->"
VERIFICATION_END = "<!-- /loreport:verification -->"

INTEGRATIONS_PENDING = "<!-- loreport:section:integrations:pending -->"
DRIFT_PENDING = "<!-- loreport:section:drift:pending -->"
DETAILS_PENDING = "<!-- loreport:section:details:pending -->"

STATUS_PENDING = "loreport:pending"
CLAIM_PLACEHOLDER = "loreport:claim:pending"

SECTION_HUMAN_DOC = "human-doc"
SECTION_VERIFICATION = "code-verification"
SECTION_DETAILS = "details"
SECTION_INDEX_SECTIONS = "doc-sections"
SECTION_INTEGRATIONS = "integrations"
SECTION_DRIFT_SUMMARY = "drift-summary"
SECTION_DRIFT_TITLE = "drift"
SECTION_DRIFT_CRITICAL = "critical"
SECTION_DRIFT_WARNING = "warning"
SECTION_DRIFT_INFO = "info"

TABLE_COL_CLAIM = "claim"
TABLE_COL_CODE = "code"
TABLE_COL_STATUS = "status"


def section_marker(slug: str) -> str:
    return f"<!-- loreport:section:{slug} -->"


def section_heading(slug: str, *, level: int = 2) -> str:
    hashes = "#" * level
    return f"{section_marker(slug)}\n{hashes} {slug}"


def aspect_link_label(aspect_id: str) -> str:
    return aspect_id
