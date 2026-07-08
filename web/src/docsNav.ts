export type DocTreeNode = {
  path: string;
  name: string;
  children: DocTreeNode[] | null;
};

export type ServiceDocGroup = {
  name: string;
  docs: DocTreeNode[];
  driftPath: string | null;
};

export type ParsedDocNav = {
  platformDocs: DocTreeNode[];
  serviceGroups: ServiceDocGroup[];
  legacyServiceDocs: DocTreeNode[];
  allDocs: DocTreeNode[];
};

function isMarkdownLeaf(node: DocTreeNode): boolean {
  return !node.children?.length && node.name.endsWith(".md");
}

function collectLeaves(nodes: DocTreeNode[]): DocTreeNode[] {
  const out: DocTreeNode[] = [];
  for (const node of nodes) {
    if (node.children?.length) {
      out.push(...collectLeaves(node.children));
    } else if (isMarkdownLeaf(node)) {
      out.push(node);
    }
  }
  return out;
}

function findNode(nodes: DocTreeNode[], name: string): DocTreeNode | undefined {
  return nodes.find((node) => node.name === name);
}

export function parseDocTree(tree: DocTreeNode[]): ParsedDocNav {
  const platformDocs: DocTreeNode[] = [];
  const serviceGroups: ServiceDocGroup[] = [];
  const legacyServiceDocs: DocTreeNode[] = [];

  for (const node of tree) {
    if (node.name === "services" && node.children?.length) {
      for (const child of node.children) {
        if (child.children?.length) {
          const docs = child.children.filter(isMarkdownLeaf);
          const driftPath = docs.find((doc) => doc.name === "drift.md")?.path ?? null;
          serviceGroups.push({ name: child.name, docs, driftPath });
        } else if (isMarkdownLeaf(child)) {
          legacyServiceDocs.push(child);
        }
      }
      continue;
    }
    if (isMarkdownLeaf(node)) {
      platformDocs.push(node);
    } else if (node.children?.length) {
      platformDocs.push(...collectLeaves([node]));
    }
  }

  const allDocs = [
    ...platformDocs,
    ...legacyServiceDocs,
    ...serviceGroups.flatMap((group) => group.docs),
  ];

  return { platformDocs, serviceGroups, legacyServiceDocs, allDocs };
}

export function defaultDocPath(nav: ParsedDocNav): string | null {
  return (
    nav.platformDocs.find((doc) => doc.path === "quickstart.md")?.path ??
    nav.platformDocs[0]?.path ??
    nav.serviceGroups[0]?.docs.find((doc) => doc.name === "index.md")?.path ??
    nav.serviceGroups[0]?.docs[0]?.path ??
    nav.legacyServiceDocs[0]?.path ??
    nav.allDocs[0]?.path ??
    null
  );
}

export function aspectLabel(filename: string): string {
  const base = filename.replace(/\.md$/, "");
  if (base === "index") return "Обзор";
  if (base === "drift") return "Расхождения";
  if (base === "api-surface") return "API";
  return base.replace(/-/g, " ");
}

export function sortAspectDocs(docs: DocTreeNode[]): DocTreeNode[] {
  const order = ["index.md", "drift.md"];
  return [...docs].sort((a, b) => {
    const ai = order.indexOf(a.name);
    const bi = order.indexOf(b.name);
    if (ai !== -1 || bi !== -1) {
      return (ai === -1 ? 99 : ai) - (bi === -1 ? 99 : bi);
    }
    return a.name.localeCompare(b.name);
  });
}
