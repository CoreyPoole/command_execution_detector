"""Summarize CEDE output on pinned external projects without asserting ground truth."""
import json
import sys
from pathlib import Path


def summarize(folder: Path) -> str:
    rows = ["| Project | Rust files | Findings | High | Medium | Low | Parse errors |",
            "|---|---:|---:|---:|---:|---:|---:|"]
    for path in sorted(folder.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))["summary"]
        rows.append(
            f"| {path.stem} | {data['files_scanned']} | {data['findings']} | "
            f"{data['High']} | {data['Medium']} | {data['Low']} | "
            f"{data['skipped_files']} |"
        )
    rows += ["", "Findings are **unreviewed candidates**, not confirmed",
             "vulnerabilities. Manual labeling is required to estimate",
             "precision or recall on these external projects."]
    return "\n".join(rows) + "\n"


if __name__ == "__main__":
    print(summarize(Path(sys.argv[1] if len(sys.argv) > 1 else "reports")))
