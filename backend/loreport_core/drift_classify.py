from __future__ import annotations

import json

from loreport_core.compile_markers import (
    SECTION_DRIFT_BLOCKER,
    SECTION_DRIFT_FIX_CODE,
    SECTION_DRIFT_FIX_DOC,
    SECTION_DRIFT_RESPOND,
)

# Language-agnostic drift classes (classify step output).
CLASS_MATCH = "match"
CLASS_STUB_OK = "stub-ok"
CLASS_DOC_LIES = "doc-lies"
CLASS_DOC_GAP = "doc-gap"
CLASS_CODE_GAP = "code-gap"
CLASS_AMBIGUOUS = "ambiguous"

DROP_CLASSES = frozenset({CLASS_MATCH, CLASS_STUB_OK})
VERIFY_CLASSES = frozenset({CLASS_DOC_LIES, CLASS_AMBIGUOUS})

CLASS_TO_SEVERITY: dict[str, str] = {
    CLASS_DOC_LIES: SECTION_DRIFT_BLOCKER,
    CLASS_AMBIGUOUS: SECTION_DRIFT_RESPOND,
    CLASS_DOC_GAP: SECTION_DRIFT_FIX_DOC,
    CLASS_CODE_GAP: SECTION_DRIFT_FIX_CODE,
}

# Structural signal — always English slug (independent of OUTPUT LANGUAGE prose).
SIGNAL_ALIGNED = "aligned"
SIGNAL_SILENCE = "silence"
SIGNAL_CONTRADICTION = "contradiction"
SIGNAL_DOC_AHEAD = "doc-ahead"
SIGNAL_CODE_MISSING = "code-missing"
SIGNAL_STUB = "stub"
SIGNAL_UNCLEAR = "unclear"

DRIFT_SIGNALS: tuple[str, ...] = (
    SIGNAL_ALIGNED,
    SIGNAL_SILENCE,
    SIGNAL_CONTRADICTION,
    SIGNAL_DOC_AHEAD,
    SIGNAL_CODE_MISSING,
    SIGNAL_STUB,
    SIGNAL_UNCLEAR,
)

# English-only fallback when classifier omits signal (should be rare).
_SILENT_DOC_MARKERS: tuple[str, ...] = (
    "mentions only",
    "only describes",
    "does not describe",
    "does not mention",
    "silent on",
    "no mention of",
    "not reflected in",
)

_DOC_AHEAD_MARKERS: tuple[str, ...] = (
    "should be documented",
    "needs to be documented",
    "expand readme",
    "in documentation",
)

_CODE_MISSING_MARKERS: tuple[str, ...] = (
    "missing in code",
    "not implemented",
    "code does not",
)


def normalize_drift_class(
    *,
    drift_class: str,
    signal: str | None = None,
    human_doc: str = "",
    issue: str = "",
) -> str:
    """Downgrade common LLM misclassifications before severity mapping."""
    sig = (signal or "").strip().lower()

    if drift_class == CLASS_DOC_LIES:
        if sig in {SIGNAL_SILENCE, SIGNAL_STUB, SIGNAL_DOC_AHEAD, SIGNAL_ALIGNED}:
            return CLASS_DOC_GAP
        combined = f"{human_doc} {issue}".lower()
        if any(marker in combined for marker in _SILENT_DOC_MARKERS):
            return CLASS_DOC_GAP

    if drift_class == CLASS_CODE_GAP:
        if sig in {SIGNAL_DOC_AHEAD, SIGNAL_SILENCE, SIGNAL_STUB, SIGNAL_ALIGNED}:
            return CLASS_DOC_GAP
        if sig == SIGNAL_CODE_MISSING:
            return CLASS_CODE_GAP
        iss = issue.lower()
        if any(marker in iss for marker in _DOC_AHEAD_MARKERS):
            return CLASS_DOC_GAP
        mentions_docs = "readme" in iss or "document" in iss
        code_missing = any(marker in iss for marker in _CODE_MISSING_MARKERS)
        if mentions_docs and not code_missing:
            return CLASS_DOC_GAP

    return drift_class


DRIFT_CLASSIFY_RULES = """
Drift classification (structural — apply BEFORE writing drift.md):

Classes:
- `match` — human doc and code agree; DROP (not drift)
- `stub-ok` — doc says not wired/not implemented; code is stub/TODO without side-effect; DROP
- `doc-lies` — doc **explicitly asserts** X; inspected code **contradicts** X; → 🔴 blocker
- `doc-gap` — code has X; human doc **silent** (no claim, no contradiction); → 🟡 fix-doc
- `code-gap` — human doc **asserts/promises** X; code **missing**; → 🟢 fix-code
- `ambiguous` — stub vs feature, API vs UI scope, env default vs example; → 🟠 respond

Signal (required, ALWAYS English slug — not translated):
- `aligned` — doc and code agree on the topic
- `silence` — human doc omits topic; code implements it
- `contradiction` — human doc asserts X; code proves otherwise
- `doc-ahead` — code implements X; docs should describe it
- `code-missing` — human doc promises X; implementation absent
- `stub` — endpoint/TODO stub without expected side-effects
- `unclear` — team must decide scope (stub vs feature, API vs UI)

Critical distinction (doc-lies vs doc-gap):
- signal `silence` or `doc-ahead` → never `doc-lies`
- `doc-lies` requires signal `contradiction` (false claim in human doc)
- Silence, omission, thin README = doc-gap even when issue sounds serious

Critical distinction (doc-gap vs code-gap):
- signal `doc-ahead` → doc-gap, NOT code-gap
- code-gap requires signal `code-missing`

Structural rules:
- HTTP route without publish/enqueue/persist side-effect = stub, not "implemented"
- Webhook stub with TODO, README silent on webhooks = ambiguous or stub-ok, NOT doc-lies
- API exists but UI missing = doc-gap or ambiguous, NOT doc-lies
- Example `LOREPORT_LANGUAGE=ru` in README with code default `en` = ambiguous, NOT blocker
- Phrases like "no drift found" or "matches implementation" = match → DROP

FORBIDDEN in drift.md:
- Rows for match or stub-ok classes
- Rows stating "no divergence found"
- 🔴 blocker rows where signal is silence/doc-ahead (use 🟡 fix-doc)
""".strip()


def drift_normalize_js_helpers() -> str:
    """JS helpers injected into eval workflow — keep in sync with normalize_drift_class."""
    silent_signals = json.dumps(
        [SIGNAL_SILENCE, SIGNAL_STUB, SIGNAL_DOC_AHEAD, SIGNAL_ALIGNED]
    )
    doc_ahead_signals = json.dumps(
        [SIGNAL_DOC_AHEAD, SIGNAL_SILENCE, SIGNAL_STUB, SIGNAL_ALIGNED]
    )
    silent_markers = json.dumps(list(_SILENT_DOC_MARKERS), ensure_ascii=False)
    doc_ahead_markers = json.dumps(list(_DOC_AHEAD_MARKERS), ensure_ascii=False)
    code_missing_markers = json.dumps(list(_CODE_MISSING_MARKERS), ensure_ascii=False)
    return f"""
function normalizeDriftClass(item) {{
  const sig = (item.signal || "").toLowerCase();
  const hd = (item.humanDoc || "").toLowerCase();
  const issue = (item.issue || "").toLowerCase();
  const combined = hd + " " + issue;
  const silentSignals = new Set({silent_signals});
  const docAheadSignals = new Set({doc_ahead_signals});
  const silentMarkers = {silent_markers};
  const docAheadMarkers = {doc_ahead_markers};
  const codeMissingMarkers = {code_missing_markers};
  let driftClass = item.driftClass;
  if (driftClass === "doc-lies") {{
    if (silentSignals.has(sig)) driftClass = "doc-gap";
    else if (silentMarkers.some((m) => combined.includes(m))) driftClass = "doc-gap";
  }}
  if (driftClass === "code-gap") {{
    if (docAheadSignals.has(sig)) driftClass = "doc-gap";
    else if (sig === "code-missing") driftClass = "code-gap";
    else if (docAheadMarkers.some((m) => issue.includes(m))) driftClass = "doc-gap";
    else {{
      const mentionsDocs = issue.includes("readme") || issue.includes("document");
      const codeMissing = codeMissingMarkers.some((m) => issue.includes(m));
      if (mentionsDocs && !codeMissing) driftClass = "doc-gap";
    }}
  }}
  return driftClass;
}}
""".strip()
