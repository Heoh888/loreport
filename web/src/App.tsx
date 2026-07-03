import { useCallback, useEffect, useState } from "react";

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
  poll_interval_sec: number;
  language: string;
  languages: LanguageOption[];
};

type DocTreeNode = {
  path: string;
  name: string;
  children: DocTreeNode[] | null;
};

function flattenDocs(nodes: DocTreeNode[]): DocTreeNode[] {
  const out: DocTreeNode[] = [];
  for (const node of nodes) {
    if (node.children?.length) {
      out.push(...flattenDocs(node.children));
    } else {
      out.push(node);
    }
  }
  return out;
}

function formatDate(value: string | null): string | null {
  if (!value) return null;
  return new Date(value).toLocaleString();
}

export function App() {
  const [status, setStatus] = useState<SyncStatus | null>(null);
  const [settings, setSettings] = useState<AppSettings | null>(null);
  const [language, setLanguage] = useState("en");
  const [docs, setDocs] = useState<DocTreeNode[]>([]);
  const [selectedPath, setSelectedPath] = useState<string | null>(null);
  const [docHtml, setDocHtml] = useState<string>("");
  const [docLoading, setDocLoading] = useState(false);
  const [loading, setLoading] = useState(false);

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
    const flat = flattenDocs(tree);
    setSelectedPath((current) => {
      if (current && flat.some((doc) => doc.path === current)) {
        return current;
      }
      const quickstart = flat.find((doc) => doc.path === "quickstart.md");
      return quickstart?.path ?? flat[0]?.path ?? null;
    });
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
    if (selectedPath) {
      void loadDocContent(selectedPath);
    }
  }, [loadDocContent, selectedPath]);

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

  const flatDocs = flattenDocs(docs);
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
          <p className="muted">Init на большом репозитории может занять 10–30 минут. Следи за логами контейнера.</p>
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
        {flatDocs.length === 0 ? (
          <p className="muted">
            Пока нет файлов в <code>loreport/</code>. Выбери язык и нажми Init.
          </p>
        ) : (
          <div className="docs-layout">
            <nav className="docs-nav">
              {flatDocs.map((doc) => (
                <button
                  key={doc.path}
                  type="button"
                  className={doc.path === selectedPath ? "doc-link active" : "doc-link"}
                  onClick={() => setSelectedPath(doc.path)}
                >
                  {doc.name.replace(/\.md$/, "")}
                </button>
              ))}
            </nav>
            <article className="doc-content">
              {docLoading ? (
                <p className="muted">Загрузка…</p>
              ) : (
                <div
                  className="markdown-body"
                  dangerouslySetInnerHTML={{ __html: docHtml }}
                />
              )}
            </article>
          </div>
        )}
      </section>
    </main>
  );
}
