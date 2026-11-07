"""Regression tests for exporting findings from the desktop interface."""
import json
from pathlib import Path
from types import SimpleNamespace

from cede import gui
from cede.models import Severity
from cede.report_exporter import ReportExporter
from cede.scan_controller import ScanController


SAMPLES = Path(__file__).resolve().parents[1] / "samples"


def test_gui_export_includes_findings_hidden_by_filter(tmp_path, monkeypatch):
    report = ScanController().scan_file(SAMPLES / "vulnerable.rs")
    output = tmp_path / "findings.json"

    monkeypatch.setattr(gui.filedialog, "asksaveasfilename", lambda **kwargs: str(output))
    messages = []
    monkeypatch.setattr(gui.messagebox, "showinfo", lambda *args: messages.append(args))

    # Invoke the event handler without constructing a Tk window.
    window = SimpleNamespace(
        report=report,
        exporter=ReportExporter(),
        _shown=report.filter_by(Severity.HIGH),
    )
    assert len(window._shown) < len(report.findings)

    gui.MainWindow.on_export(window)

    exported = json.loads(output.read_text(encoding="utf-8"))
    assert exported["summary"]["findings"] == len(report.findings)
    assert len(exported["findings"]) == len(report.findings)
    assert {entry["severity"] for entry in exported["findings"]} == {"High", "Low"}
    assert messages
