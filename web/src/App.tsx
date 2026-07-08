import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { docPathFromLocation, docUrl, resolveDocLink, wireDocLinks } from "./docLinks";
import {
  aspectLabel,
  defaultDocPath,
  parseDocTree,
  sortAspectDocs,
  type DocTreeNode,
  type ServiceDocGroup,
} from "./docsNav";
import { renderMermaidIn } from "./renderMermaid";

type SyncStatus = {
  state: string;
  last_run: string | null;
  head: string | null;
  changed: boolean | null;
  error: string | null;
};

type LanguageOption = {
  code: string;
  label: string;
};

type AppSettings = {
  provider: string;
  model_id: string | null;
  language: string;
  languages: LanguageOption[];
};

function formatDate(value: string | null): string | null {
  if (!value) return null;
  return new Date(value).toLocaleString();
}

function findServiceForPath(groups: ServiceDocGroup[], path: string | null): string | null {
  if (!path) return null;
  const match = groups.find((group) => path.startsWith(`services/${group.name}/`));
  return match?.name ?? null;
}

export function App() {
  const [status, setStatus] = useState<SyncStatus | null>(null);
  const [settings, setSettings] = useState<AppSettings | null>(null);
  const [language, setLanguage] = useState("en");
  const [docs, setDocs] = useState<DocTreeNode[]>([]);
  const [selectedPath, setSelectedPath] = useState<string | null>(null);
  const [selectedService, setSelectedService] = useState<string | null>(null);
  const [docHtml, setDocHtml] = useState<string>("");
  const [docLoading, setDocLoading] = useState(false);
  const [loading, setLoading] = useState(false);
  const docContentRef = useRef<HTMLDivElement>(null);

  const docNav = useMemo(() => parseDocTree(docs), [docs]);
  const docPathSet = useMemo(() => new Set(docNav.allDocs.map((doc) => doc.path)), [docNav.allDocs]);

  const activeService = useMemo(() => {
    if (selectedService) {
      return docNav.serviceGroups.find((group) => group.name === selectedService) ?? null;
    }
    return null;
  }, [docNav.serviceGroups, selectedService]);

  const selectDoc = useCallback(
    (path: string, historyMode: "push" | "replace" = "push") => {
      setSelectedPath(path);
      const service = findServiceForPath(docNav.serviceGroups, path);
      if (service) {
        setSelectedService(service);
      }
      const url = docUrl(path);
      if (window.location.pathname === url) {
        return;
      }
      const state = { docPath: path };
      if (historyMode === "replace") {
        window.history.replaceState(state, "", url);
      } else {
        window.history.pushState(state, "", url);
      }
    },
    [docNav.serviceGroups],
  );

  const loadSettings = useCallback(async () => {
    const res = await fetch("/api/settings");
    const data = (await res.json()) as AppSettings;
    setSettings(data);
    setLanguage(data.language);
  }, []);

  const loadStatus = useCallback(async () => {
    const res = await fetch("/api/sync/status");
    setStatus(await res.json());
  }, []);

  const loadDocs = useCallback(async () => {
    const res = await fetch("/api/docs/tree");
    if (!res.ok) return;
    const tree = (await res.json()) as DocTreeNode[];
    setDocs(tree);

    const nav = parseDocTree(tree);
    const paths = new Set(nav.allDocs.map((doc) => doc.path));
    const fromUrl = docPathFromLocation(window.location.pathname, paths);

    setSelectedPath((current) => {
      if (fromUrl) {
        return fromUrl;
      }
      if (current && paths.has(current)) {
        return current;
      }
      return defaultDocPath(nav);
    });

    setSelectedService((current) => {
      const resolved = fromUrl ?? defaultDocPath(nav);
      return findServiceForPath(nav.serviceGroups, resolved) ?? current;
    });

    const resolved = fromUrl ?? defaultDocPath(nav);
    if (resolved) {
      window.history.replaceState({ docPath: resolved }, "", docUrl(resolved));
    }
  }, []);

  const loadDocContent = useCallback(async (path: string) => {
    setDocLoading(true);
    try {
      const res = await fetch(`/api/docs/render?path=${encodeURIComponent(path)}`);
      if (!res.ok) {
        setDocHtml("<p>Не удалось загрузить документ.</p>");
        return;
      }
      const data = (await res.json()) as { html: string };
      setDocHtml(data.html);
    } finally {
      setDocLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadSettings();
    void loadStatus();
    void loadDocs();
    const id = setInterval(() => {
      void loadStatus();
    }, 5000);
    return () => clearInterval(id);
  }, [loadDocs, loadSettings, loadStatus]);

  useEffect(() => {
    if (status?.state === "idle" && status.changed) {
      void loadDocs();
    }
  }, [loadDocs, status?.changed, status?.state]);

  useEffect(() => {
    const onPopState = () => {
      const path = docPathFromLocation(window.location.pathname, docPathSet);
      if (path) {
        setSelectedPath(path);
        setSelectedService(findServiceForPath(docNav.serviceGroups, path));
      }
    };
    window.addEventListener("popstate", onPopState);
    return () => window.removeEventListener("popstate", onPopState);
  }, [docNav.serviceGroups, docPathSet]);

  useEffect(() => {
    if (selectedPath) {
      void loadDocContent(selectedPath);
    }
  }, [loadDocContent, selectedPath]);

  useEffect(() => {
    const el = docContentRef.current;
    if (!el || docLoading || !docHtml || !selectedPath) return;
    el.innerHTML = docHtml;
    wireDocLinks(el, selectedPath, docPathSet);
    void renderMermaidIn(el);
  }, [docHtml, docLoading, docPathSet, selectedPath]);

  useEffect(() => {
    const el = docContentRef.current;
    if (!el || !selectedPath) return;

    const onClick = (event: MouseEvent) => {
      const anchor = (event.target as HTMLElement).closest("a");
      if (!anchor || !el.contains(anchor)) return;

      const href = anchor.getAttribute("href");
      if (!href) return;

      const docPath = resolveDocLink(selectedPath, href);
      if (docPath && docPathSet.has(docPath)) {
        event.preventDefault();
        selectDoc(docPath);
      }
    };

    el.addEventListener("click", onClick);
    return () => el.removeEventListener("click", onClick);
  }, [docPathSet, docHtml, docLoading, selectDoc, selectedPath]);

  async function trigger(command: "init" | "update") {
    setLoading(true);
    try {
      await fetch("/api/sync/trigger", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ command, language }),
      });
      await loadStatus();
    } finally {
      setLoading(false);
    }
  }

  function openService(group: ServiceDocGroup) {
    setSelectedService(group.name);
    const preferred =
      group.docs.find((doc) => doc.name === "index.md")?.path ??
      group.docs.find((doc) => doc.name !== "drift.md")?.path ??
      group.docs[0]?.path;
    if (preferred) {
      selectDoc(preferred);
    }
  }

  const statusLabel =
    status?.state === "running"
      ? "выполняется"
      : status?.state === "error"
        ? "ошибка"
        : status?.state === "idle"
          ? "готов"
          : (status?.state ?? "…");

  return (
    <main className="page">
      <header>
        <h1>Loreport</h1>
        <p>Живая документация репозитория.</p>
      </header>

      <section className="card sync-card">
        <h2>Sync</h2>
        <p>
          Статус: <strong>{statusLabel}</strong>
        </p>
        {status?.last_run && (
          <p className="muted">Последний запуск: {formatDate(status.last_run)}</p>
        )}
        {status?.changed != null && status.state === "idle" && (
          <p className="muted">
            {status.changed ? "Документация обновлена" : "Изменений не было"}
          </p>
        )}
        {status?.head && status.head !== "HEAD" && (
          <p className="mono">HEAD {status.head.slice(0, 12)}…</p>
        )}
        {status?.state === "running" && (
          <p className="muted">
            Init на большом репозитории может занять 10–30 минут. Следи за логами контейнера.
          </p>
        )}
        {status?.error && <p className="error">{status.error}</p>}

        <label className="field">
          <span>Язык документации</span>
          <select
            value={language}
            onChange={(event) => setLanguage(event.target.value)}
            disabled={loading || status?.state === "running"}
          >
            {(settings?.languages ?? [{ code: "ru", label: "Русский" }]).map((option) => (
              <option key={option.code} value={option.code}>
                {option.label}
              </option>
            ))}
          </select>
        </label>

        <div className="actions">
          <button
            disabled={loading || status?.state === "running"}
            onClick={() => void trigger("update")}
          >
            Sync now
          </button>
          <button
            disabled={loading || status?.state === "running"}
            onClick={() => void trigger("init")}
          >
            Init
          </button>
          <button type="button" onClick={() => void loadDocs()}>
            Обновить список
          </button>
        </div>
        {settings && (
          <p className="muted small">
            Provider: {settings.provider}
            {settings.model_id ? ` · ${settings.model_id}` : ""}
          </p>
        )}
      </section>

      <section className="card docs-card">
        <h2>Документация</h2>
        {docNav.allDocs.length === 0 ? (
          <p className="muted">
            Пока нет файлов в <code>loreport/</code>. Выбери язык и нажми Init.
          </p>
        ) : (
          <div className="docs-layout">
            <nav className="docs-nav">
              {docNav.platformDocs.length > 0 && (
                <div className="docs-nav-section">
                  <span className="docs-nav-title">Платформа</span>
                  {docNav.platformDocs.map((doc) => (
                    <button
                      key={doc.path}
                      type="button"
                      className={doc.path === selectedPath ? "doc-link active" : "doc-link"}
                      onClick={() => selectDoc(doc.path)}
                    >
                      {aspectLabel(doc.name)}
                    </button>
                  ))}
                </div>
              )}

              {docNav.serviceGroups.length > 0 && (
                <div className="docs-nav-section">
                  <span className="docs-nav-title">Сервисы</span>
                  {docNav.serviceGroups.map((group) => (
                    <button
                      key={group.name}
                      type="button"
                      className={
                        selectedService === group.name ? "doc-link active service-link" : "doc-link service-link"
                      }
                      onClick={() => openService(group)}
                    >
                      {group.name}
                    </button>
                  ))}
                </div>
              )}

              {docNav.legacyServiceDocs.length > 0 && (
                <div className="docs-nav-section">
                  <span className="docs-nav-title">Legacy</span>
                  {docNav.legacyServiceDocs.map((doc) => (
                    <button
                      key={doc.path}
                      type="button"
                      className={doc.path === selectedPath ? "doc-link active" : "doc-link"}
                      onClick={() => selectDoc(doc.path)}
                    >
                      {aspectLabel(doc.name)}
                    </button>
                  ))}
                </div>
              )}
            </nav>

            <div className="docs-main">
              {activeService && (
                <nav className="aspect-tabs">
                  {sortAspectDocs(activeService.docs).map((doc) => (
                    <button
                      key={doc.path}
                      type="button"
                      className={
                        doc.path === selectedPath
                          ? "aspect-tab active"
                          : doc.name === "drift.md"
                            ? "aspect-tab drift-tab"
                            : "aspect-tab"
                      }
                      onClick={() => selectDoc(doc.path)}
                    >
                      {aspectLabel(doc.name)}
                    </button>
                  ))}
                </nav>
              )}
              <article className="doc-content">
                {docLoading ? (
                  <p className="muted">Загрузка…</p>
                ) : (
                  <div
                    ref={docContentRef}
                    className={
                      selectedPath?.endsWith("/drift.md")
                        ? "markdown-body drift-view"
                        : "markdown-body"
                    }
                  />
                )}
              </article>
            </div>
          </div>
        )}
      </section>
    </main>
  );
}
