"""Tkinter dashboard for comparing CEDE findings with test-suite manifests."""
import queue
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from .testing_dashboard import CaseResult, SuiteResult, evaluate_suite


def _default_suite() -> str:
    for base in (Path.cwd(), Path(__file__).resolve().parent.parent):
        path = base / "rust_corpus"
        if (path / "manifest.json").is_file():
            return str(path)
    return ""


class TestingDashboardWindow(tk.Toplevel):
    """Independent regression runner; does not overwrite the main scan report."""

    def __init__(self, parent, rules=None):
        super().__init__(parent)
        self.title("CEDE — Test Dashboard")
        self.geometry("1050x620")
        self.minsize(760, 460)
        self.rules = rules
        self.suite_path = tk.StringVar(value=_default_suite())
        self.only_failures = tk.BooleanVar(value=False)
        self.summary = tk.StringVar(value="Select rust_corpus or rust_projects, then Run Tests.")
        self.progress_text = tk.StringVar(value="No test run yet.")
        self._results: queue.Queue = queue.Queue()
        self._cancel = threading.Event()
        self._running = False
        self.result: SuiteResult | None = None
        self._visible: list[CaseResult] = []
        self._build()
        self.protocol("WM_DELETE_WINDOW", self._close)

    def _build(self):
        outer = ttk.Frame(self, padding=12)
        outer.pack(fill="both", expand=True)

        ttk.Label(outer, text="Rust regression testing", font=("TkDefaultFont", 15, "bold")).pack(anchor="w")
        ttk.Label(outer, text="Compare CEDE's actual findings against the included test manifests. "
                  "This does not execute Rust code.").pack(anchor="w", pady=(2, 10))
        location = ttk.Frame(outer)
        location.pack(fill="x", pady=(0, 8))
        ttk.Label(location, text="Test suite:").pack(side="left", padx=(0, 6))
        ttk.Entry(location, textvariable=self.suite_path).pack(side="left", fill="x", expand=True)
        self.browse_button = ttk.Button(location, text="Browse…", command=self._browse)
        self.browse_button.pack(side="left", padx=(6, 0))

        controls = ttk.Frame(outer)
        controls.pack(fill="x", pady=(0, 10))
        self.run_button = ttk.Button(controls, text="Run Tests", command=self.start_run)
        self.run_button.pack(side="left")
        self.cancel_button = ttk.Button(controls, text="Cancel", command=self.cancel_run, state="disabled")
        self.cancel_button.pack(side="left", padx=6)
        ttk.Checkbutton(controls, text="Show failures only", variable=self.only_failures,
                        command=self._populate).pack(side="right")

        ttk.Label(outer, textvariable=self.summary, font=("TkDefaultFont", 11, "bold")).pack(
            anchor="w", pady=(0, 5))
        ttk.Label(outer, textvariable=self.progress_text).pack(anchor="w", pady=(0, 8))
        self.progress_bar = ttk.Progressbar(outer, mode="determinate", maximum=100)
        self.progress_bar.pack(fill="x", pady=(0, 10))

        table_frame = ttk.Frame(outer)
        table_frame.pack(fill="both", expand=True)
        columns = ("result", "case", "expected", "actual")
        self.table = ttk.Treeview(table_frame, columns=columns, show="headings", selectmode="browse")
        for field, width in (("result", 100), ("case", 300), ("expected", 250), ("actual", 250)):
            self.table.heading(field, text=field.title())
            self.table.column(field, width=width, stretch=(field != "result"))
        self.table.tag_configure("PASS", foreground="#27835b")
        self.table.tag_configure("FAIL", foreground="#c0392b")
        self.table.tag_configure("SKIP", foreground="#be8610")
        self.table.pack(side="left", fill="both", expand=True)
        scroll = ttk.Scrollbar(table_frame, orient="vertical", command=self.table.yview)
        scroll.pack(side="right", fill="y")
        self.table.configure(yscrollcommand=scroll.set)
        self.table.bind("<<TreeviewSelect>>", lambda _event: self._show_detail())

        ttk.Label(outer, text="Selected case details:").pack(anchor="w", pady=(10, 3))
        self.detail = tk.Text(outer, height=4, wrap="word", state="disabled")
        self.detail.pack(fill="x")
        ttk.Label(
            outer, text="PASS = matches expected result. SKIP = expected invalid Rust. "
                        "FAIL = unexpected result. Curated fixtures are not real-world accuracy data.",
            wraplength=1000
        ).pack(anchor="w", pady=(8, 0))

    def _browse(self):
        path = filedialog.askdirectory(parent=self, title="Select rust_corpus or rust_projects")
        if path:
            self.suite_path.set(path)

    def start_run(self):
        if self._running:
            return
        root = Path(self.suite_path.get()).expanduser()
        if not (root / "manifest.json").is_file():
            messagebox.showerror("Test Dashboard", "Select the rust_corpus or rust_projects "
                                 "folder containing manifest.json.", parent=self)
            return

        self._running = True
        self._cancel = threading.Event()
        self.result = None
        self._visible = []
        self.table.delete(*self.table.get_children())
        self._set_detail("Evaluating test cases…")
        self.progress_bar.configure(value=0)
        self.summary.set("Running test suite…")
        self.progress_text.set(str(root))
        self.run_button.state(["disabled"])
        self.browse_button.state(["disabled"])
        self.cancel_button.state(["!disabled"])

        def worker():
            try:
                report = evaluate_suite(
                    root, rules=self.rules, cancel=self._cancel.is_set,
                    progress=lambda count, total, name: self._results.put(
                        ("progress", count, total, name)
                    ),
                )
                self._results.put(("done", report, None))
            except Exception as exc:
                self._results.put(("done", None, exc))
        threading.Thread(target=worker, daemon=True).start()
        self.after(50, self._poll)

    def cancel_run(self):
        if self._running:
            self._cancel.set()
            self.progress_text.set("Cancelling after the current test…")

    def _poll(self):
        while True:
            try:
                message = self._results.get_nowait()
            except queue.Empty:
                break
            if message[0] == "progress":
                _, count, total, name = message
                self.progress_bar.configure(value=100 * count / total)
                self.progress_text.set(f"Tested {count}/{total}: {name}")
                continue

            _, report, error = message
            self._running = False
            self.run_button.state(["!disabled"])
            self.browse_button.state(["!disabled"])
            self.cancel_button.state(["disabled"])
            if error is not None:
                self.summary.set("Testing failed")
                self.progress_text.set(str(error))
                messagebox.showerror("Test Dashboard", str(error), parent=self)
            else:
                self.result = report
                self.summary.set(
                    f"{report.passed} passed  •  {report.failed} failed  •  "
                    f"{report.skipped} expected parse errors"
                )
                state = "Cancelled" if report.cancelled else "Complete"
                self.progress_text.set(
                    f"{state}: {report.processed}/{report.total} cases evaluated — {report.suite}"
                )
                self._populate()

        if self._running:
            self.after(50, self._poll)

    def _populate(self):
        self.table.delete(*self.table.get_children())
        self._visible = []
        if self.result is not None:
            self._visible = [
                c for c in self.result.cases
                if not self.only_failures.get() or c.status == "FAIL"
            ]
            for i, case in enumerate(self._visible):
                self.table.insert("", "end", iid=str(i), tags=(case.status,),
                                  values=(case.status, case.name, case.expected, case.actual))
        self._set_detail("Select a case to inspect its result.")

    def _show_detail(self):
        selected = self.table.selection()
        if not selected:
            return
        case = self._visible[int(selected[0])]
        self._set_detail(
            f"Case: {case.name}\nExpected: {case.expected}\n"
            f"Observed: {case.actual}\nResult: {case.status}\n{case.details}"
        )

    def _set_detail(self, value):
        self.detail.configure(state="normal")
        self.detail.delete("1.0", "end")
        self.detail.insert("end", value)
        self.detail.configure(state="disabled")

    def _close(self):
        self._cancel.set()
        self.destroy()
