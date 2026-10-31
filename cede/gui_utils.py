"""Non-graphical GUI helpers; safe to test without a display server."""
from pathlib import Path


def source_context(file: Path, line: int, radius: int = 3) -> str:
    """Show numbered nearby source lines without executing Rust code."""
    try:
        lines = Path(file).read_text(encoding="utf-8", errors="replace").splitlines()
    except OSError:
        return "(Source file no longer available)"
    if not lines or line < 1 or line > len(lines):
        return "(No source context available)"
    start = max(1, line - radius)
    end = min(len(lines), line + radius)
    return "\n".join(
        f"{'>' if i == line else ' '} {i:4d} | {lines[i - 1]}"
        for i in range(start, end + 1)
    )
