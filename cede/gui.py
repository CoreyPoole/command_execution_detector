"""MainWindow: Tkinter GUI matching the SDS mockup (scan commands, severity filter, findings table, detail pane)."""
import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from .detection_rules import DetectionRules
from .models import Finding, ParseError, Severity, VulnerabilityReport
from .report_exporter import ReportExporter
from .scan_controller import ScanController
from .gui_utils import source_context

_COLORS = {Severity.HIGH: "#c0392b", Severity.MEDIUM: "#d68910", Severity.LOW: "#2874a6"}


class MainWindow(tk.Tk):
    def __init__(self, controller: ScanController | None = None):
        super().__init__()
        self.title(">_ Command Execution Detector")
        self.geometry("1150x620")
        self.minsize(800, 420)
        self.controller = controller or ScanController()
        self.exporter = ReportExporter()
        self.report = VulnerabilityReport()
        self.filter: Severity | None = None
        self._shown: list[Finding] = []
        self._results: queue.Queue = queue.Queue()
        self._busy = False
        self._cancel_event = threading.Event()
        self._scan_buttons = []
        self._build_ui()
        self._refresh()

    # ---- layout -----------------------------------------------------------
    def _build_ui(self):
        bar = ttk.Frame(self, padding=8)
        bar.pack(fill="x")
        for text, cmd in [("Scan File", self.on_scan_file), ("Scan Project", self.on_scan_project),
                          ("Export Report", self.on_export), ("Detection Rules", self.on_rules)]:
            button = ttk.Button(bar, text=text, command=cmd)
            button.pack(side="left", padx=(0, 6))
            if text.startswith("Scan "):
                self._scan_buttons.append(button)
        self.cancel_button = ttk.Button(bar, text="Cancel Scan",
                                        command=self.on_cancel, state="disabled")
        self.cancel_button.pack(side="left", padx=(0, 6))
        ttk.Button(bar, text="Test Dashboard", command=self.on_test_dashboard).pack(
            side="left", padx=(0, 6)
        )

        self._filter_var = tk.StringVar(value="All")
        right = ttk.Frame(bar)
        right.pack(side="right")
        ttk.Label(right, text="Severity:").pack(side="left", padx=(0, 6))
        for label in ("All", "High", "Medium", "Low"):
            ttk.Radiobutton(right, text=label, value=label, variable=self._filter_var,
                            style="Toolbutton", command=self.on_filter_changed).pack(side="left", padx=2)

        panes = ttk.PanedWindow(self, orient="horizontal")
        panes.pack(fill="both", expand=True, padx=8)

        left = ttk.Frame(panes)
        cols = ("severity", "file", "line", "pattern")
        self.table = ttk.Treeview(left, columns=cols, show="headings", selectmode="browse")
        for c, w, anchor in [("severity", 80, "w"), ("file", 220, "w"), ("line", 55, "e"), ("pattern", 420, "w")]:
            self.table.heading(c, text=c.capitalize())
            self.table.column(c, width=w, anchor=anchor, stretch=(c == "pattern"))
        for sev, color in _COLORS.items():
            self.table.tag_configure(sev.value, foreground=color)
        sb = ttk.Scrollbar(left, orient="vertical", command=self.table.yview)
        self.table.configure(yscrollcommand=sb.set)
        self.table.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self.table.bind("<<TreeviewSelect>>", lambda _e: self.on_select_finding())
        panes.add(left, weight=3)

        detail = ttk.Frame(panes, padding=(10, 0, 0, 0))
        ttk.Label(detail, text="Finding detail", font=("TkDefaultFont", 11, "bold")).pack(anchor="w")
        self.detail = tk.Text(detail, wrap="word", width=42, height=10, relief="flat", state="disabled",
                              padx=4, pady=6, font=("TkDefaultFont", 11))
        self.detail.pack(fill="both", expand=True)
        self.detail.tag_configure("label", font=("TkDefaultFont", 11, "bold"))
        for sev, color in _COLORS.items():
            self.detail.tag_configure(sev.value, foreground=color, font=("TkDefaultFont", 11, "bold"))
        panes.add(detail, weight=2)

        self.status = tk.StringVar()
        ttk.Label(self, textvariable=self.status, padding=8, anchor="w").pack(fill="x")

    # ---- SDS event handlers -----------------------------------------------
    def on_scan_file(self):
        path = filedialog.askopenfilename(title="Select a Rust source file",
                                          filetypes=[("Rust source", "*.rs"), ("All files", "*.*")])
        if path:
            self._scan_file(Path(path))

    def on_scan_project(self):
        root = filedialog.askdirectory(title="Select project root")
        if not root:
            return
        n = len(self.controller.scanner.discover_rs_files(Path(root)))
        if n == 0:
            messagebox.showinfo("Scan Project", f"No .rs files found under\n{root}")
            return
        choice = self._dialog("Scan project", f"Project root: {root}\nFound {n} .rs files.", ["Cancel", "Scan"])
        if choice == "Scan":
            self.status.set(f"Scanning {n} files…")
            self._run_async(
                lambda: self.controller.scan_project(
                    Path(root), progress=self._report_progress,
                    cancel=self._cancel_event.is_set
                ),
                self._show_report,
            )

    def on_cancel(self):
        if self._busy:
            self._cancel_event.set()
            self.status.set("Cancelling scan…")

    def _report_progress(self, current, total, file):
        # This callback may be invoked on the worker thread.
        self._results.put(("progress", current, total, file))

    def on_test_dashboard(self):
        from .testing_dashboard_gui import TestingDashboardWindow
        dashboard = TestingDashboardWindow(self, rules=self.controller.rules)
        return dashboard

    def on_filter_changed(self):
        label = self._filter_var.get()
        self.filter = None if label == "All" else Severity(label)
        self._refresh()

    def on_select_finding(self):
        sel = self.table.selection()
        if sel:
            self._show_detail(self._shown[int(sel[0])])

    def on_export(self):
        if not self.report.findings and not self.report.parse_errors:
            messagebox.showinfo("Export Report", "There is nothing to export yet. Run a scan first.")
            return
        path = filedialog.asksaveasfilename(title="Export report", defaultextension=".txt",
                                            filetypes=[("Text report", "*.txt"), ("JSON report", "*.json")])
        if path:
            try:
                self.exporter.save(self.report, Path(path), self._shown)
                messagebox.showinfo("Export Report", f"Report saved to\n{path}")
            except OSError as e:
                messagebox.showerror("Export Report", str(e))

    def on_rules(self):
        path = filedialog.askopenfilename(title="Load detection rules (JSON)",
                                          filetypes=[("JSON", "*.json"), ("All files", "*.*")])
        if not path:
            return
        try:
            self.controller.set_rules(DetectionRules.load(Path(path)))
            self.status.set(f"Detection rules loaded from {Path(path).name}. Re-run a scan to apply them.")
        except (OSError, ValueError) as e:
            messagebox.showerror("Detection Rules", f"Could not load rules:\n{e}")

    def show_parse_error(self, e: ParseError):
        text = f"{e.path.name}: parse error at line {e.line} – {e.message}"
        if self._dialog("Parse error (invalid syntax)", text, ["Skip File", "Re-scan"]) == "Re-scan":
            self._scan_file(e.path)
        else:
            self.status.set(f"Skipped {e.path.name} (parse error at line {e.line}).")

    # ---- internals ---------------------------------------------------------
    def _scan_file(self, path: Path):
        self.status.set(f"Scanning {path.name}…")
        self._run_async(lambda: self.controller.scan_file(path), self._show_report)

    def _show_report(self, report: VulnerabilityReport):
        self.report = report
        self._refresh()

    def _refresh(self):
        self._shown = self.report.filter_by(self.filter)
        self.table.delete(*self.table.get_children())
        for i, f in enumerate(self._shown):
            self.table.insert("", "end", iid=str(i), tags=(f.severity.value,),
                              values=(f.severity.value, self._short(f.file), f.line, f.pattern))
        self._show_detail(None)
        self.status.set(self.exporter.summary(self.report) if self.report.files_scanned or self.report.parse_errors
                        else "Choose Scan File or Scan Project to begin.")

    @staticmethod
    def _short(path: Path) -> str:
        parts = Path(path).parts
        return "/".join(parts[-2:]) if len(parts) > 1 else str(path)

    def _show_detail(self, f: Finding | None):
        self.detail.configure(state="normal")
        self.detail.delete("1.0", "end")
        if f is None:
            self.detail.insert("end", "Select a finding to see its details.")
        else:
            for label, value, tag in [("File: ", str(f.file), None), ("Line: ", str(f.line), None),
                                      ("Severity: ", f.severity.value, f.severity.value),
                                      ("Pattern: ", f.pattern, None), ("Reason: ", f.reason, None),
                                      ("Remediation: ", f.remediation, None),
                                      ("Source context: ", source_context(f.file, f.line), None)]:
                self.detail.insert("end", label, "label")
                self.detail.insert("end", value + "\n\n", tag or ())
        self.detail.configure(state="disabled")

    def _run_async(self, work, done):
        """One scan at a time; worker threads never touch Tk widgets."""
        if self._busy:
            return
        self._busy = True
        self._cancel_event = threading.Event()
        for button in self._scan_buttons:
            button.state(["disabled"])
        self.cancel_button.state(["!disabled"])

        def target():
            try:
                self._results.put(("done", done, work(), None))
            except Exception as exc:  # Worker errors are shown on the UI thread.
                self._results.put(("done", done, None, exc))
        threading.Thread(target=target, daemon=True).start()
        self.after(50, self._poll)

    def _poll(self):
        while True:
            try:
                message = self._results.get_nowait()
            except queue.Empty:
                break
            if message[0] == "progress":
                _, current, total, file = message
                if not self._cancel_event.is_set():
                    self.status.set(f"Scanning {current}/{total}: {file.name}")
                continue

            _, done, result, exc = message
            self._busy = False
            for button in self._scan_buttons:
                button.state(["!disabled"])
            self.cancel_button.state(["disabled"])
            if self._cancel_event.is_set():
                self.status.set("Scan cancelled; previous results retained.")
            elif exc is None:
                done(result)
            elif isinstance(exc, ParseError):
                self.status.set("Parse error.")
                self.show_parse_error(exc)
            else:
                self.status.set("Scan failed.")
                messagebox.showerror("Scan failed", str(exc))
        if self._busy:
            self.after(50, self._poll)

    def _dialog(self, title: str, message: str, buttons: list[str]) -> str:
        win = tk.Toplevel(self)
        win.title(title)
        win.transient(self)
        win.resizable(False, False)
        result = {"v": buttons[0]}
        ttk.Label(win, text=title, font=("TkDefaultFont", 11, "bold"), padding=(14, 12, 14, 2)).pack(anchor="w")
        ttk.Label(win, text=message, padding=(14, 0, 14, 10), wraplength=420, justify="left").pack(anchor="w")
        row = ttk.Frame(win, padding=(14, 0, 14, 12))
        row.pack(anchor="e", fill="x")
        for b in reversed(buttons):
            def choose(b=b):
                result["v"] = b
                win.destroy()
            ttk.Button(row, text=b, command=choose).pack(side="right", padx=(6, 0))
        win.protocol("WM_DELETE_WINDOW", win.destroy)
        win.grab_set()
        self.wait_window(win)
        return result["v"]


def main():
    MainWindow().mainloop()


if __name__ == "__main__":
    main()
