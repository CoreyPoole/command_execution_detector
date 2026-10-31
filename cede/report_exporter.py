"""ReportExporter: renders a VulnerabilityReport as text (one finding per line) or JSON."""
import json
from pathlib import Path
from .models import VulnerabilityReport


class ReportExporter:
    def summary(self, r: VulnerabilityReport) -> str:
        c = {k.value: v for k, v in r.counts().items()}
        s = (f"Scanned {r.files_scanned} files · {len(r.findings)} findings "
             f"({c['High']} High, {c['Medium']} Medium, {c['Low']} Low)")
        if r.parse_errors:
            s += f" · {len(r.parse_errors)} file(s) skipped (parse error)"
        return s

    def to_text(self, r: VulnerabilityReport, findings=None) -> str:
        rows = r.findings if findings is None else findings
        lines = [
            f"{f.severity.value.upper():<6} | {f.file}:{f.line} | {f.pattern} | {f.reason} | Fix: {f.remediation}"
            for f in rows
        ]
        lines += [f"SKIPPED | {e.path}:{e.line} | {e.message}" for e in r.parse_errors]
        lines.append(self.summary(r))
        return "\n".join(lines) + "\n"

    def to_json(self, r: VulnerabilityReport, findings=None) -> str:
        rows = r.findings if findings is None else findings
        data = {
            "summary": {"files_scanned": r.files_scanned, "findings": len(r.findings),
                        **{k.value: v for k, v in r.counts().items()},
                        "skipped_files": len(r.parse_errors)},
            "findings": [{"file": str(f.file), "line": f.line, "pattern": f.pattern,
                          "severity": f.severity.value, "reason": f.reason,
                          "remediation": f.remediation} for f in rows],
            "parse_errors": [{"file": str(e.path), "line": e.line, "message": e.message} for e in r.parse_errors],
        }
        return json.dumps(data, indent=2)

    def save(self, r: VulnerabilityReport, path: Path, findings=None, fmt: str | None = None) -> None:
        path = Path(path)
        use_json = (fmt == "json") if fmt is not None else path.suffix.lower() == ".json"
        text = self.to_json(r, findings) if use_json else self.to_text(r, findings)
        path.write_text(text, encoding="utf-8")
