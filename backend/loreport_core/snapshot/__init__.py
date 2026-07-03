import hashlib
from pathlib import Path

from loreport_core.constants import LOREPORT_DIR, UPDATE_METADATA_FILE


def _hash_directory(root: Path) -> str:
    digest = hashlib.sha256()
    if not root.is_dir():
        return digest.hexdigest()

    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue
        if path.name == UPDATE_METADATA_FILE:
            continue
        rel = path.relative_to(root).as_posix().encode()
        digest.update(rel)
        digest.update(path.read_bytes())
    return digest.hexdigest()


def create_loreport_content_snapshot(repo_path: Path, loreport_dir: str = LOREPORT_DIR) -> str:
    return _hash_directory(repo_path / loreport_dir)
