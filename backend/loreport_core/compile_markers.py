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
STATUS_MATCH = "loreport:match"
STATUS_DRIFT = "loreport:drift"
STATUS_MISSING_CODE = "loreport:missing-code"
STATUS_MISSING_DOC = "loreport:missing-doc"
CLAIM_PLACEHOLDER = "loreport:claim:pending"

DRIFT_NONE = "<!-- loreport:drift:none -->"
DRIFT_TRAFFIC_LEGEND = (
    "> 🔴 **blocker** doc≠code · 🟠 **respond** team decision · "
    "🟡 **fix-doc** · 🟢 **fix-code**"
)

SECTION_HUMAN_DOC = "human-doc"
SECTION_DETAILS = "details"
SECTION_INDEX_SECTIONS = "doc-sections"
SECTION_INTEGRATIONS = "integrations"
SECTION_DRIFT_SUMMARY = "drift-summary"
SECTION_DRIFT_TITLE = "drift"
SECTION_DRIFT_BLOCKER = "blocker"
SECTION_DRIFT_RESPOND = "respond"
SECTION_DRIFT_FIX_DOC = "fix-doc"
SECTION_DRIFT_FIX_CODE = "fix-code"
# Legacy slugs (v0.2–v0.3 beta drift files)
SECTION_DRIFT_HIGH = "high"
SECTION_DRIFT_LOW = "low"
SECTION_DRIFT_CRITICAL = "critical"
SECTION_DRIFT_WARNING = "warning"
SECTION_DRIFT_INFO = "info"

TABLE_COL_ASPECT = "aspect"
TABLE_COL_HUMAN = "human-doc"
TABLE_COL_CODE = "code"
TABLE_COL_ISSUE = "issue"
TABLE_COL_CLAIM = "claim"
TABLE_COL_STATUS = "status"
SECTION_VERIFICATION = "code-verification"

DRIFT_SEVERITY_SLUGS = (
    SECTION_DRIFT_BLOCKER,
    SECTION_DRIFT_RESPOND,
    SECTION_DRIFT_FIX_DOC,
    SECTION_DRIFT_FIX_CODE,
)


def section_marker(slug: str) -> str:
    return f"<!-- loreport:section:{slug} -->"


def section_heading(slug: str, *, level: int = 2, label: str | None = None) -> str:
    hashes = "#" * level
    display = label if label is not None else slug
    return f"{section_marker(slug)}\n{hashes} {display}"


def drift_severity_table_header() -> str:
    return (
        f"| {TABLE_COL_ASPECT} | {TABLE_COL_HUMAN} | {TABLE_COL_CODE} | {TABLE_COL_ISSUE} |"
        "\n| --- | --- | --- | --- |"
    )


def aspect_link_label(aspect_id: str) -> str:
    return aspect_id
