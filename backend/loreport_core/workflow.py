from __future__ import annotations

import json

from loreport_core.constants import language_label, resolve_language
from loreport_core.language import output_language_policy
from loreport_core.scope import RepoScope, ServiceScope

SERVICE_RESEARCH_SCHEMA: dict[str, object] = {
    "type": "object",
    "properties": {
        "serviceName": {"type": "string"},
        "implementationPathCount": {
            "type": "number",
            "description": "Count of distinct code file paths in implementation signals",
        },
        "shallow": {
            "type": "boolean",
            "description": "True if research is doc-only or has excuses like not read in this pass",
        },
        "markdownNotes": {
            "type": "string",
            "description": "Full per-service integrity research in OUTPUT LANGUAGE",
        },
        "gapCount": {"type": "number"},
    },
    "required": ["serviceName", "implementationPathCount", "shallow", "markdownNotes"],
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

MIN_IMPLEMENTATION_PATHS = 5
MAX_SERVICE_RETRIES = 2


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
        f"Set shallow=true if < {MIN_IMPLEMENTATION_PATHS} paths "
        f"or if you used phrases like 'not read in this pass'."
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

    return f"""
// Loreport map-reduce init workflow — execute verbatim via eval
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
    const paths = last?.implementationPathCount ?? 0;
    const shallow = last?.shallow === true;
    if (paths >= MIN_PATHS && !shallow) break;
  }}
  return {{ service: name, meta, ...last }};
}}

const results = [];
for (let i = 0; i < services.length; i += BATCH_SIZE) {{
  const batch = services.slice(i, i + BATCH_SIZE);
  const batchResults = await Promise.all(batch.map((name) => researchOne(name)));
  results.push(...batchResults);
}}

const shallowServices = results
  .filter((r) => (r.implementationPathCount ?? 0) < MIN_PATHS || r.shallow === true)
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

    return f"""
// Loreport targeted update workflow — execute verbatim via eval
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
    const paths = last?.implementationPathCount ?? 0;
    if (paths >= MIN_PATHS && last?.shallow !== true) break;
  }}
  return {{ service: name, ...last }};
}}

let results = [];
for (let pass = 0; pass < MAX_PASSES; pass++) {{
  const pending = pass === 0 ? services : results
    .filter((r) => (r.implementationPathCount ?? 0) < MIN_PATHS || r.shallow === true)
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
        "Write or update loreport/services/*.md from results[].markdownNotes, "
        "then quickstart and platform from platform.markdownSynthesis."
        if command == "init"
        else "Update only affected loreport/services/*.md from results[].markdownNotes."
    )
    return f"""
Deterministic workflow (Eval map-reduce):

1. Call the `eval` tool ONCE with the JavaScript below — execute it verbatim.
2. Do NOT write your own orchestration loop; the script already covers batches and retries.
3. {action}
4. Rewrite all prose into OUTPUT LANGUAGE before write_file — never paste markdownNotes verbatim.

{lang_policy}

```javascript
{script}
```
""".strip()
