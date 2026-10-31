"""Exercise the real Tkinter window under Xvfb in GitHub Actions."""
import os
import sys
import threading
import time
import tkinter as tk
import pytest

pytestmark = pytest.mark.skipif(
    sys.platform.startswith("linux") and not os.environ.get("DISPLAY"),
    reason="GUI integration requires Xvfb or a graphical display",
)

from cede.gui import MainWindow
from cede.models import VulnerabilityReport


def test_scan_cancellation_keeps_window_responsive():
    try:
        window = MainWindow()
    except tk.TclError as exc:
        raise AssertionError("CI virtual display must support Tkinter") from exc
    window.withdraw()
    release = threading.Event()

    try:
        window._run_async(
            lambda: (release.wait(2), VulnerabilityReport())[1],
            window._show_report,
        )
        assert window._busy
        assert "disabled" in window._scan_buttons[0].state()
        assert "disabled" not in window.cancel_button.state()

        window.on_cancel()
        release.set()
        deadline = time.monotonic() + 4
        while window._busy and time.monotonic() < deadline:
            window.update()
            time.sleep(0.01)
        assert not window._busy
        assert "cancel" in window.status.get().lower()
        assert "disabled" not in window._scan_buttons[0].state()
        assert "disabled" in window.cancel_button.state()
    finally:
        release.set()
        window.destroy()


def test_testing_dashboard_evaluates_and_filters_real_tk_window(tmp_path):
    """Drive the dashboard using a display in the dedicated Xvfb CI job."""
    import json

    root = tmp_path / "rust_corpus"
    root.mkdir()
    (root / "clean.rs").write_text(
        'fn main(){ std::process::Command::new("echo").arg("ok").status().unwrap(); }'
    )
    (root / "broken.rs").write_text("fn broken( {")
    (root / "manifest.json").write_text(json.dumps({"cases": [
        {"path": "rust_corpus/clean.rs", "expected": "High"},
        {"path": "rust_corpus/broken.rs", "expected": "ParseError"},
    ]}))

    window = MainWindow()
    window.withdraw()
    dashboard = None
    try:
        dashboard = window.on_test_dashboard()
        dashboard.withdraw()
        dashboard.suite_path.set(str(root))
        dashboard.start_run()
        assert dashboard._running
        assert "disabled" in dashboard.run_button.state()

        deadline = time.monotonic() + 5
        while dashboard._running and time.monotonic() < deadline:
            window.update()
            time.sleep(0.01)

        assert dashboard.result is not None
        assert dashboard.result.failed == 1
        assert dashboard.result.skipped == 1
        assert len(dashboard.table.get_children()) == 2
        assert "1 failed" in dashboard.summary.get()
        dashboard.only_failures.set(True)
        dashboard._populate()
        assert len(dashboard.table.get_children()) == 1
        assert "disabled" not in dashboard.run_button.state()
        assert window.report.findings == []
    finally:
        if dashboard is not None:
            dashboard._close()
        window.destroy()
