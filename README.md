# Command Execution Detector (CEDE)

Static analysis tool that scans **Rust** source code for unsafe operating-system command execution
(command injection). Written in Python; uses `tree-sitter-rust` to parse Rust so comments and doc
strings are never matched.

## Setup
    pip install -r requirements.txt        # GUI also needs Tkinter (included with python.org / macOS Python)

## Use
    python -m cede samples                         # scan a project folder or a single .rs file
    python -m cede samples/vulnerable.rs --min-severity high
    python -m cede samples --format json -o report.json
    python -m cede samples --rules my_rules.json   # custom detection rules
    python -m cede --dump-default-rules > my_rules.json   # starting point for custom rules
    python -m cede --gui                           # graphical interface (or: python -m cede.gui)

Exit status: 0 = ok, 1 = a finding at/above `--fail-on` (default high), 2 = bad input.

## Tests
    python -m pytest tests

## Layout (maps to the SDS class diagram)
| Module | SDS class(es) |
|---|---|
| `cede/file_scanner.py` | FileScanner |
| `cede/rust_parser.py` | RustParser, SyntaxTree (ParseError in models) |
| `cede/detection_rules.py` | DetectionRules |
| `cede/sink_detector.py` | SinkDetector, Sink |
| `cede/taint_analyzer.py` | TaintAnalyzer, TaintPath, SourceKind |
| `cede/severity_scorer.py` | SeverityScorer, Severity |
| `cede/scan_controller.py` | ScanController |
| `cede/models.py` | Finding, VulnerabilityReport, Severity, SourceKind, ParseError, Sink, TaintPath |
| `cede/report_exporter.py` | ReportExporter |
| `cede/cli.py` | CliApp |
| `cede/gui.py` | MainWindow |

## Known limits
- Taint tracking is per function, is order-aware for simple straight-line statements, and cannot generally trace values passed through function parameters or calls to other functions.
- External sanitizer functions are recognized by configured names; local sanitizers are only accepted when their bodies match a narrowly recognized alphanumeric-filter pattern. This is not a proof of security.
- Simple `use std::process::Command as Cmd` aliases are recognized; more complex import resolution is not supported.
- The analyzer is intentionally heuristic; evaluate findings and potential false negatives manually.
