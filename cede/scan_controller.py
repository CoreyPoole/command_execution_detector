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
from .project_analysis import ProjectLinker


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
        return self._scan_tree(path, tree)

    def _scan_tree(self, path, tree, external_params=None, external_returns=None):
        sinks = self.sink_detector.find_sinks(tree)
        report = VulnerabilityReport(files_scanned=1)
        # Use an isolated analysis instance per file. This also prevents
        # overlapping GUI scans from sharing mutable taint caches.
        analyzer = TaintAnalyzer(self.rules)
        for tp in analyzer.trace(tree, sinks, external_params, external_returns):
            if not self.scorer.should_report(tp):
                continue
            report.findings.append(Finding(
                file=path, line=tp.sink.line, pattern=tp.sink.api,
                severity=self.scorer.score(tp),
                reason=self.scorer.reason(tp), remediation=self.scorer.remediation(tp),
            ))
        self._sort(report)
        return report

    def scan_project(self, root: Path, progress: Callable[[int, int, Path], None] | None = None,
                     cancel: Callable[[], bool] | None = None) -> VulnerabilityReport:
        """Scan every .rs file under root. Files with syntax errors are skipped and recorded."""
        root = Path(root)
        files = self.scanner.discover_rs_files(root)
        report = VulnerabilityReport()
        trees = {}
        # Parse once, then resolve unambiguous module calls across files.
        for f in files:
            if cancel is not None and cancel():
                return report
            try:
                trees[f] = self.parser.parse(self.scanner.read_file(f), f)
            except ParseError as exc:
                report.parse_errors.append(exc)
        params, returns = ProjectLinker(
            root if root.is_dir() else root.parent, trees, self.rules
        ).resolve()
        for i, f in enumerate(files, 1):
            if cancel is not None and cancel():
                break
            if f in trees:
                report.merge(self._scan_tree(
                    f, trees[f], params.get(f), returns.get(f)
                ))
            if progress:
                progress(i, len(files), f)
        self._sort(report)
        return report

    @staticmethod
    def _sort(report: VulnerabilityReport) -> None:
        report.findings.sort(key=lambda f: (f.severity.rank, str(f.file), f.line))
