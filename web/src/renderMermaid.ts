import mermaid from "mermaid";

let initialized = false;
let renderCounter = 0;

function ensureMermaid(): void {
  if (initialized) return;
  mermaid.initialize({
    startOnLoad: false,
    theme: "dark",
    securityLevel: "loose",
  });
  initialized = true;
}

function extractMermaidBlocks(container: HTMLElement): HTMLElement[] {
  const blocks: HTMLElement[] = [];
  container.querySelectorAll("pre > code.language-mermaid").forEach((code) => {
    const pre = code.parentElement;
    if (!pre) return;
    const div = document.createElement("div");
    div.className = "mermaid";
    div.textContent = code.textContent ?? "";
    pre.replaceWith(div);
    blocks.push(div);
  });
  return blocks;
}

function showMermaidError(block: HTMLElement, source: string): void {
  const pre = document.createElement("pre");
  pre.className = "mermaid-error";
  const code = document.createElement("code");
  code.textContent = source;
  pre.appendChild(code);
  const note = document.createElement("p");
  note.className = "muted small";
  note.textContent = "Не удалось отрисовать Mermaid-диаграмму.";
  const wrapper = document.createElement("div");
  wrapper.className = "mermaid-fallback";
  wrapper.append(note, pre);
  block.replaceWith(wrapper);
}

export async function renderMermaidIn(container: HTMLElement): Promise<void> {
  ensureMermaid();

  const blocks = extractMermaidBlocks(container);
  if (blocks.length === 0) return;

  await Promise.all(
    blocks.map(async (block) => {
      const source = block.textContent ?? "";
      if (!source.trim()) return;
      const id = `loreport-mermaid-${++renderCounter}`;
      try {
        const { svg, bindFunctions } = await mermaid.render(id, source);
        block.innerHTML = svg;
        bindFunctions?.(block);
      } catch {
        showMermaidError(block, source);
      }
    }),
  );
}
