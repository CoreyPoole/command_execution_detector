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
