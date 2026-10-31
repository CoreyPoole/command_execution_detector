"""ScanController: coordinates scanning one file or a whole project (SDS sequences 4.1-4.3)."""
from pathlib import Path
from typing import Callable
from .detection_rules import DetectionRules
from .file_scanner import FileScanner
from .models import Finding, ParseError, VulnerabilityReport
from .rust_parser import RustParser
from .severity_scorer import SeverityScorer
from .sink_detector import SinkDetector
from .taint_analyzer import TaintAnalyzer


class ScanController:
    def __init__(self, rules: DetectionRules | None = None):
        self.scanner = FileScanner()
        self.parser = RustParser()
        self.scorer = SeverityScorer()
        self.set_rules(rules or DetectionRules())

    def set_rules(self, rules: DetectionRules) -> None:
        """Configure Detection Rules use case: swap rules between scans."""
        self.rules = rules
        self.sink_detector = SinkDetector(rules)
        self.taint = TaintAnalyzer(rules)

    def scan_file(self, path: Path) -> VulnerabilityReport:
        """Scan one file. Raises ParseError if the file has a syntax error (use case 4.3)."""
        path = Path(path)
        source = self.scanner.read_file(path)
        tree = self.parser.parse(source, path)
        sinks = self.sink_detector.find_sinks(tree)
        report = VulnerabilityReport(files_scanned=1)
        for tp in self.taint.trace(tree, sinks):
            if not self.scorer.should_report(tp):
                continue
            report.findings.append(Finding(
                file=path, line=tp.sink.line, pattern=tp.sink.api,
                severity=self.scorer.score(tp),
                reason=self.scorer.reason(tp), remediation=self.scorer.remediation(tp),
            ))
        self._sort(report)
        return report

    def scan_project(self, root: Path, progress: Callable[[int, int, Path], None] | None = None) -> VulnerabilityReport:
        """Scan every .rs file under root. Files with syntax errors are skipped and recorded."""
        files = self.scanner.discover_rs_files(Path(root))
        report = VulnerabilityReport()
        for i, f in enumerate(files, 1):
            try:
                report.merge(self.scan_file(f))
            except ParseError as e:
                report.parse_errors.append(e)
            if progress:
                progress(i, len(files), f)
        self._sort(report)
        return report

    @staticmethod
    def _sort(report: VulnerabilityReport) -> None:
        report.findings.sort(key=lambda f: (f.severity.rank, str(f.file), f.line))
