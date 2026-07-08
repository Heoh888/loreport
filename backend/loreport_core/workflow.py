from __future__ import annotations

import json

from loreport_core.constants import language_label, resolve_language
from loreport_core.integrity import MIN_SOURCE_FILE_PATHS
from loreport_core.language import output_language_policy
from loreport_core.scope import RepoScope, ServiceScope

SERVICE_RESEARCH_SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {
        "serviceName": {"type": "string"},
        "implementationPathCount": {
            "type": "number",
            "description": "Count of opened files in readPathsInImplementation",
        },
        "shallow": {
            "type": "boolean",
            "description": (
                "True if doc-only, too few opened files, "
                "or citedPathsInGaps not covered by opened files"
            ),
        },
        "readPathsInImplementation": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Repo-relative files opened with read_file (not directories)",
        },
        "citedPathsInGaps": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Repo-relative local paths named in Gaps & drift items",
        },
        "markdownNotes": {
            "type": "string",
            "description": "Full per-service integrity research in OUTPUT LANGUAGE",
        },
        "gapCount": {"type": "number"},
    },
    "required": [
        "serviceName",
        "implementationPathCount",
        "shallow",
        "markdownNotes",
        "readPathsInImplementation",
        "citedPathsInGaps",
    ],
}

PLATFORM_WRITER_SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {
        "markdownSynthesis": {
            "type": "string",
            "description": "Platform synthesis in OUTPUT LANGUAGE",
        },
        "shallowServices": {
            "type": "array",
            "items": {"type": "string"},
        },
    },
    "required": ["markdownSynthesis", "shallowServices"],
}

MIN_IMPLEMENTATION_PATHS = MIN_SOURCE_FILE_PATHS
MAX_SERVICE_RETRIES = 3

_SHALLOW_JS_HELPERS = """
function normalizePath(path) {{
  return (path || "").replace(/^`+|`+$/g, "").replace(/^\\//, "").toLowerCase().replace(/\\/$/, "");
}}

function isRepoFilePath(path) {{
  const norm = normalizePath(path);
  if (!norm) return false;
  const base = norm.split("/").pop();
  return base.includes(".");
}}

function filterSourceFiles(paths) {{
  return (paths || []).filter((path) => isRepoFilePath(path));
}}

function citationIsCovered(cited, readPaths) {{
  const citedNorm = normalizePath(cited);
  if (!citedNorm) return true;
  const readFiles = filterSourceFiles(readPaths).map(normalizePath);
  if (isRepoFilePath(cited)) return readFiles.includes(citedNorm);
  const dirPrefix = citedNorm + "/";
  return readFiles.some((readFile) => readFile.startsWith(dirPrefix));
}}

function resultIsShallow(result) {{
  const readPaths = result?.readPathsInImplementation ?? [];
  const citedPaths = result?.citedPathsInGaps ?? [];
  const openedFiles = filterSourceFiles(readPaths);
  const unreadCited = citedPaths.filter((path) => !citationIsCovered(path, readPaths));
  const paths = result?.implementationPathCount ?? openedFiles.length;
  return result?.shallow === true || paths < MIN_PATHS || unreadCited.length > 0;
}}
""".strip()


def _service_meta(service: ServiceScope) -> dict[str, object]:
    return {
        "path": f"/{service.name}/",
        "techDocs": service.has_tech_docs,
        "readme": service.has_readme,
    }


def build_service_meta_map(scope: RepoScope) -> dict[str, dict[str, object]]:
    return {service.name: _service_meta(service) for service in scope.services}


def build_service_task_description(
    service: ServiceScope,
    *,
    language: str | None = None,
    attempt: int = 0,
) -> str:
    code = resolve_language(language)
    label = language_label(code)
    hints: list[str] = []
    if service.has_tech_docs:
        hints.append("Read tech.docs/ and README for intent, then verify in code.")
    else:
        hints.append("No tech.docs — code-first: entrypoint, routers, consumers, config, models.")
    if service.has_readme:
        hints.append("README present.")
    if attempt > 0:
        hints.append(
            f"RETRY {attempt}: prior pass was shallow. Read models/routers you cited. "
            f"Min {MIN_IMPLEMENTATION_PATHS} code paths."
        )
    return (
        f"Inspect service `{service.name}` at `/{service.name}/`. "
        f"{' '.join(hints)} "
        f"Return full integrity notes in {label}. "
        f"Count implementation paths honestly. "
        f"Set shallow=true if < {MIN_IMPLEMENTATION_PATHS} opened files "
        f"or citedPathsInGaps not covered by opened files in readPathsInImplementation."
    )


def build_map_reduce_init_script(
    scope: RepoScope,
    *,
    language: str | None = None,
    max_parallel: int = 5,
    min_paths: int = MIN_IMPLEMENTATION_PATHS,
    max_retries: int = MAX_SERVICE_RETRIES,
) -> str:
    services = list(scope.service_names)
    meta = build_service_meta_map(scope)
    descriptions = {
        name: build_service_task_description(
            next(s for s in scope.services if s.name == name),
            language=language,
        )
        for name in services
    }
    lang_code = resolve_language(language)
    shallow_helpers = _SHALLOW_JS_HELPERS

    return f"""
// Loreport map-reduce init workflow — execute verbatim via eval
{shallow_helpers}

const services = {json.dumps(services, ensure_ascii=False)};
const serviceMeta = {json.dumps(meta, ensure_ascii=False)};
const taskDescriptions = {json.dumps(descriptions, ensure_ascii=False)};
const BATCH_SIZE = {max_parallel};
const MIN_PATHS = {min_paths};
const MAX_RETRIES = {max_retries};
const OUTPUT_LANGUAGE = {json.dumps(lang_code)};

const researchSchema = {json.dumps(SERVICE_RESEARCH_SCHEMA, ensure_ascii=False)};
const platformSchema = {json.dumps(PLATFORM_WRITER_SCHEMA, ensure_ascii=False)};

function buildRetryDescription(name, attempt) {{
  const base = taskDescriptions[name];
  return (
    base + " RETRY " + attempt + ": read every file you cite; min "
    + MIN_PATHS + " code paths."
  );
}}

async function researchOne(name) {{
  const meta = serviceMeta[name];
  let last = null;
  for (let attempt = 0; attempt <= MAX_RETRIES; attempt++) {{
    const description = attempt === 0
      ? taskDescriptions[name]
      : buildRetryDescription(name, attempt);
    last = await task({{
      description,
      subagentType: "service-researcher",
      label: name,
      responseSchema: researchSchema,
    }});
    if (!resultIsShallow(last)) break;
  }}
  return {{ service: name, meta, ...last, stillShallow: resultIsShallow(last) }};
}}

const results = [];
for (let i = 0; i < services.length; i += BATCH_SIZE) {{
  const batch = services.slice(i, i + BATCH_SIZE);
  const batchResults = await Promise.all(batch.map((name) => researchOne(name)));
  results.push(...batchResults);
}}

const shallowServices = results
  .filter((r) => r.stillShallow === true)
  .map((r) => r.service);

const platform = await task({{
  description:
    "Synthesize platform integrity overview in OUTPUT_LANGUAGE " + OUTPUT_LANGUAGE +
    " from these per-service results. Flag shallow services: " +
    JSON.stringify(shallowServices) +
    ". Full payload: " + JSON.stringify(results),
  subagentType: "platform-writer",
  label: "platform-synthesis",
  responseSchema: platformSchema,
}});

({{
  workflow: "map-reduce-init",
  servicesProcessed: results.length,
  shallowServices,
  results,
  platform,
}});
""".strip()


def build_map_reduce_update_script(
    scope: RepoScope,
    affected_services: tuple[str, ...],
    *,
    language: str | None = None,
    max_parallel: int = 5,
    max_passes: int = 3,
    min_paths: int = MIN_IMPLEMENTATION_PATHS,
    max_retries: int = MAX_SERVICE_RETRIES,
) -> str:
    services = list(affected_services)
    known = {s.name for s in scope.services}
    filtered = [name for name in services if name in known]
    meta = {
        name: _service_meta(next(s for s in scope.services if s.name == name))
        for name in filtered
    }
    descriptions = {
        name: build_service_task_description(
            next(s for s in scope.services if s.name == name),
            language=language,
        )
        + " Update integrity notes for git-changed service only."
        for name in filtered
    }
    lang_code = resolve_language(language)
    shallow_helpers = _SHALLOW_JS_HELPERS

    return f"""
// Loreport targeted update workflow — execute verbatim via eval
{shallow_helpers}

const services = {json.dumps(filtered, ensure_ascii=False)};
const serviceMeta = {json.dumps(meta, ensure_ascii=False)};
const taskDescriptions = {json.dumps(descriptions, ensure_ascii=False)};
const BATCH_SIZE = {max_parallel};
const MAX_PASSES = {max_passes};
const MIN_PATHS = {min_paths};
const MAX_RETRIES = {max_retries};
const OUTPUT_LANGUAGE = {json.dumps(lang_code)};

const researchSchema = {json.dumps(SERVICE_RESEARCH_SCHEMA, ensure_ascii=False)};

async function researchOne(name) {{
  let last = null;
  for (let attempt = 0; attempt <= MAX_RETRIES; attempt++) {{
    const suffix = attempt === 0 ? "" : " RETRY " + attempt;
    last = await task({{
      description: taskDescriptions[name] + suffix,
      subagentType: "service-researcher",
      label: name,
      responseSchema: researchSchema,
    }});
    if (!resultIsShallow(last)) break;
  }}
  return {{ service: name, ...last, stillShallow: resultIsShallow(last) }};
}}

let results = [];
for (let pass = 0; pass < MAX_PASSES; pass++) {{
  const pending = pass === 0 ? services : results
    .filter((r) => r.stillShallow === true)
    .map((r) => r.service);
  if (pending.length === 0) break;
  const passResults = [];
  for (let i = 0; i < pending.length; i += BATCH_SIZE) {{
    const batch = pending.slice(i, i + BATCH_SIZE);
    passResults.push(...(await Promise.all(batch.map((name) => researchOne(name)))));
  }}
  if (pass === 0) {{
    results = passResults;
  }} else {{
    const byName = Object.fromEntries(results.map((r) => [r.service, r]));
    for (const r of passResults) byName[r.service] = r;
    results = Object.values(byName);
  }}
}}

({{
  workflow: "map-reduce-update",
  servicesProcessed: results.length,
  results,
}});
""".strip()


def format_eval_workflow_block(
    *,
    command: str,
    script: str,
    loreport_dir: str,
    language: str | None = None,
) -> str:
    lang_policy = output_language_policy(language)
    action = (
        "Write or update loreport/services/<name>/ folders from results — "
        "index.md, drift.md, and aspect files; then quickstart and platform."
        if command == "init"
        else "Update only affected loreport/services/<name>/ folders from results."
    )
    shallow_rule = (
        "5. For services in shallowServices or with stillShallow=true: BEFORE write_file, "
        "read_file entrypoint, routes, and every cited path. "
        "Implementation signals must list opened files only — not directories.\n"
        "6. VERIFY every required file from _pattern.json exists via write_file before ending the run."
    )
    return f"""
Deterministic workflow (Eval map-reduce):

1. Call the `eval` tool ONCE with the JavaScript below — execute it verbatim.
2. Do NOT write your own orchestration loop; the script already covers batches and retries.
3. {action}
4. Rewrite all prose into OUTPUT LANGUAGE before write_file — never paste markdownNotes verbatim.
{shallow_rule}

{lang_policy}

```javascript
{script}
```
""".strip()
