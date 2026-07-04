from pathlib import Path

import markdown
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel

from loreport_server.config import Settings, get_settings

router = APIRouter(prefix="/api/docs", tags=["docs"])


class DocTreeNode(BaseModel):
    path: str
    name: str
    children: list["DocTreeNode"] | None = None


class DocContentResponse(BaseModel):
    path: str
    content: str
    updated_at: float | None = None


class DocRenderResponse(BaseModel):
    html: str


def _lore_root(settings: Settings) -> Path:
    return Path(settings.repo_path) / settings.loreport_dir


def _resolve_doc_path(root: Path, path: str) -> Path:
    file_path = (root / path).resolve()
    try:
        file_path.relative_to(root.resolve())
    except ValueError as exc:
        raise HTTPException(status_code=404, detail="Document not found") from exc
    if not file_path.is_file() or file_path.suffix != ".md":
        raise HTTPException(status_code=404, detail="Document not found")
    return file_path


def _build_tree(directory: Path, base: Path) -> list[DocTreeNode]:
    if not directory.is_dir():
        return []
    nodes: list[DocTreeNode] = []
    for entry in sorted(directory.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower())):
        if entry.name.startswith(".") or entry.name.startswith("_"):
            continue
        rel = entry.relative_to(base).as_posix()
        if entry.is_dir():
            children = _build_tree(entry, base)
            nodes.append(DocTreeNode(path=rel, name=entry.name, children=children or None))
        elif entry.suffix == ".md":
            nodes.append(DocTreeNode(path=rel, name=entry.name))
    return nodes


@router.get("/tree", response_model=list[DocTreeNode])
async def docs_tree(settings: Settings = Depends(get_settings)) -> list[DocTreeNode]:
    root = _lore_root(settings)
    return _build_tree(root, root)


@router.get("/content", response_model=DocContentResponse)
async def docs_content(
    path: str = Query(..., min_length=1),
    settings: Settings = Depends(get_settings),
) -> DocContentResponse:
    file_path = _resolve_doc_path(_lore_root(settings), path)
    stat = file_path.stat()
    return DocContentResponse(
        path=path,
        content=file_path.read_text(encoding="utf-8"),
        updated_at=stat.st_mtime,
    )


@router.get("/render", response_model=DocRenderResponse)
async def docs_render(
    path: str = Query(..., min_length=1),
    settings: Settings = Depends(get_settings),
) -> DocRenderResponse:
    file_path = _resolve_doc_path(_lore_root(settings), path)
    content = file_path.read_text(encoding="utf-8")
    return DocRenderResponse(html=markdown.markdown(content, extensions=["tables", "fenced_code"]))
