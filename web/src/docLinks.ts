const LOREPORT_PREFIX = /^loreport\//;
const DOCS_URL_PREFIX = "/docs/";

export function docUrl(path: string): string {
  return `${DOCS_URL_PREFIX}${path}`;
}

export function docPathFromLocation(pathname: string, docPaths: ReadonlySet<string>): string | null {
  if (pathname.startsWith(DOCS_URL_PREFIX)) {
    const path = decodeURIComponent(pathname.slice(DOCS_URL_PREFIX.length));
    if (docPaths.has(path)) {
      return path;
    }
  }

  const bare = pathname.startsWith("/") ? pathname.slice(1) : pathname;
  if (!bare.endsWith(".md")) {
    return null;
  }

  if (docPaths.has(bare)) {
    return bare;
  }

  const matches = [...docPaths].filter((candidate) => candidate === bare || candidate.endsWith(`/${bare}`));
  if (matches.length === 1) {
    return matches[0];
  }

  return null;
}

export function resolveDocLink(currentPath: string, href: string): string | null {
  if (!href || /^https?:\/\//i.test(href) || href.startsWith("mailto:")) {
    return null;
  }
  if (href.startsWith("#")) {
    return null;
  }

  const hashIndex = href.indexOf("#");
  const target = hashIndex >= 0 ? href.slice(0, hashIndex) : href;
  if (!target) {
    return null;
  }

  let path = target;
  if (path.startsWith(DOCS_URL_PREFIX)) {
    path = path.slice(DOCS_URL_PREFIX.length);
  }
  if (path.startsWith("/")) {
    path = path.slice(1);
  }
  if (LOREPORT_PREFIX.test(path)) {
    path = path.replace(LOREPORT_PREFIX, "");
  }

  const dirParts = currentPath.split("/");
  dirParts.pop();

  for (const segment of path.split("/")) {
    if (!segment || segment === ".") {
      continue;
    }
    if (segment === "..") {
      dirParts.pop();
      continue;
    }
    dirParts.push(segment);
  }

  const resolved = dirParts.join("/");
  if (!resolved.endsWith(".md")) {
    return null;
  }
  return resolved;
}

export function wireDocLinks(
  container: HTMLElement,
  currentPath: string,
  docPaths: ReadonlySet<string>,
): void {
  container.querySelectorAll("a[href]").forEach((node) => {
    const anchor = node as HTMLAnchorElement;
    const href = anchor.getAttribute("href");
    if (!href) {
      return;
    }

    const docPath = resolveDocLink(currentPath, href);
    if (docPath && docPaths.has(docPath)) {
      anchor.classList.add("doc-internal-link");
      anchor.dataset.docPath = docPath;
      return;
    }

    if (/^https?:\/\//i.test(href)) {
      anchor.target = "_blank";
      anchor.rel = "noopener noreferrer";
    }
  });
}
