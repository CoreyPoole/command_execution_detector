"""FileScanner: discovers .rs files and reads them."""
from pathlib import Path

SKIP_DIRS = {"target", ".git", "node_modules"}


class FileScanner:
    def discover_rs_files(self, root: Path) -> list[Path]:
        root = Path(root)
        if root.is_file():
            return [root] if root.suffix == ".rs" else []
        return sorted(
            p for p in root.rglob("*.rs")
            if not (set(p.relative_to(root).parts[:-1]) & SKIP_DIRS)
        )

    def read_file(self, path: Path) -> str:
        return Path(path).read_text(encoding="utf-8", errors="replace")
