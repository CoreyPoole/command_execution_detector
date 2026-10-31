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
- Taint tracking is order-aware for simple straight-line code and supports direct, unambiguous helper calls and return values **within one Rust file**. It does not resolve cross-file calls, traits, imports, or general control flow. Branches may be combined conservatively.
- External sanitizer functions are recognized by configured names; local sanitizers are only accepted when their bodies match a narrowly recognized alphanumeric-filter pattern. This is not a proof of security.
- Simple `use std::process::Command as Cmd` aliases are recognized; more complex import resolution is not supported.
- Command builders stored in local variables are tracked across simple method calls and repeated executions. Full Rust ownership, aliasing, and conditional execution semantics are not modeled.
- The analyzer is intentionally heuristic; evaluate findings and potential false negatives manually.

## Development and installation (v0.2)
- Use Python 3.11 or newer and run `python -m pip install -e ".[dev]"`.
- CLI: `cede samples`; desktop GUI: `cede-gui` (requires Tkinter).
- Benchmark: `python -m cede.benchmark` reports precision and recall on a
  small synthetic security regression corpus, not real-world accuracy.
- Build wheel and source distribution with `python -m build`.
- CI tests run on Windows, macOS, and Linux.

## Additional v0.2 analysis limits
- Conditional assignments and shadowing are handled conservatively; this is
  not a Rust control-flow graph or Rust borrow checker.
- Explicit module-qualified or imported same-project calls are resolved when
  unambiguous; macros, traits, wildcard imports, and reexports are not.
- GUI supports one scan at a time, progress and cancellation between files,
  plus source context for findings.

## Desktop builds (experimental)
- The `Build desktop applications` GitHub Actions workflow packages the Tkinter
  GUI for Linux, Windows, and macOS using PyInstaller. Build artifacts are
  attached to each workflow run under Actions, not uploaded to PyPI.
- Builds are unsigned, have not been manually tested on physical machines,
  and might display platform warnings. An installed Python wheel and local
  Tkinter environment remain the most reliable starting point.
- Create a release after validation by pushing a semantic `v*` Git tag.
  The release workflow publishes wheel and source-distribution assets.
