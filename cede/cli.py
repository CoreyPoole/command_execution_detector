"""CliApp: command-line interface. Prints one finding per line (SDS section 5)."""
import argparse
import sys
from pathlib import Path
from .detection_rules import DetectionRules
from .models import Severity, VulnerabilityReport
from .report_exporter import ReportExporter
from .scan_controller import ScanController

_LEVELS = {"high": Severity.HIGH, "medium": Severity.MEDIUM, "low": Severity.LOW}


class CliApp:
    def __init__(self):
        self.exporter = ReportExporter()

    def build_parser(self) -> argparse.ArgumentParser:
        p = argparse.ArgumentParser(prog="cede", description="Detect unsafe command execution in Rust source code.")
        p.add_argument("path", nargs="?", help="a .rs file or a project directory")
        p.add_argument("--min-severity", choices=_LEVELS, default="low", help="hide findings below this level")
        p.add_argument("--format", choices=["text", "json"], default="text")
        p.add_argument("-o", "--output", help="also save the report to this file (.json for JSON, otherwise text)")
        p.add_argument("--rules", help="JSON file with detection rule overrides")
        p.add_argument("--fail-on", choices=[*_LEVELS, "none"], default="high",
                       help="exit with status 1 if a finding at/above this level exists (default: high)")
        p.add_argument("--dump-default-rules", action="store_true", help="print the default rules as JSON and exit")
        p.add_argument("--gui", action="store_true", help="open the graphical interface")
        return p

    def run(self, argv: list[str] | None = None) -> int:
        args = self.build_parser().parse_args(argv)
        if args.dump_default_rules:
            print(DetectionRules().to_json())
            return 0
        try:
            rules = DetectionRules.load(Path(args.rules)) if args.rules else DetectionRules()
        except (OSError, ValueError) as e:
            print(f"error: cannot load rules: {e}", file=sys.stderr)
            return 2
        controller = ScanController(rules)
        if args.gui:
            from .gui import MainWindow
            MainWindow(controller).mainloop()
            return 0
        if not args.path:
            self.build_parser().error("a path is required (or use --gui)")
        target = Path(args.path)
        if not target.exists():
            print(f"error: {target} does not exist", file=sys.stderr)
            return 2
        if target.is_file() and target.suffix != ".rs":
            print(f"error: {target} is not a Rust (.rs) file", file=sys.stderr)
            return 2
        try:
            report = controller.scan_project(target)
        except OSError as e:
            print(f"error: {e}", file=sys.stderr)
            return 2

        shown = [f for f in report.findings if f.severity.rank <= _LEVELS[args.min_severity].rank]
        self.print_report(report, shown, args.format)
        if args.output:
            try:
                self.exporter.save(report, Path(args.output), shown, fmt=args.format)
            except OSError as e:
                print(f"error: cannot save report: {e}", file=sys.stderr)
                return 2
        if args.fail_on != "none" and any(f.severity.rank <= _LEVELS[args.fail_on].rank for f in report.findings):
            return 1
        return 0

    def print_report(self, report: VulnerabilityReport, findings=None, fmt: str = "text") -> None:
        out = self.exporter.to_json(report, findings) if fmt == "json" else self.exporter.to_text(report, findings)
        print(out, end="" if out.endswith("\n") else "\n")


def main(argv: list[str] | None = None) -> int:
    return CliApp().run(argv)
