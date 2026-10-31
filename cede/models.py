"""Shared data classes from the SDS class diagram (Severity, SourceKind, ParseError, ...)."""
from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path


class Severity(Enum):
    HIGH = "High"
    MEDIUM = "Medium"
    LOW = "Low"

    @property
    def rank(self) -> int:          # 0 = most severe
        return [Severity.HIGH, Severity.MEDIUM, Severity.LOW].index(self)


class SourceKind(Enum):
    USER_INPUT = "UserInput"
    ENV_VAR = "EnvVar"
    FILE = "File"
    NETWORK = "Network"


class ParseError(Exception):
    """Raised by RustParser when a file has a syntax error (SDS use case 4.3)."""

    def __init__(self, path: Path, line: int, message: str):
        self.path, self.line, self.message = Path(path), line, message
        super().__init__(f"{path}: parse error at line {line} - {message}")


@dataclass
class Sink:
    line: int
    api: str                      # e.g. 'Command::new("sh")'
    is_shell_invocation: bool = False
    node: object = None           # outermost syntax node of the call chain (used by the taint analyzer)
    program_node: object = None   # expression passed to Command::new(...)
    arg_nodes: list = field(default_factory=list)   # expressions passed to .arg()/.args()
    arg_sites: list = field(default_factory=list)   # (expression, source position) for temporal taint tracing
    methods: list = field(default_factory=list)     # method names in the chain, in order
    function_node: object = None  # enclosing fn (scope for taint tracing)


@dataclass
class TaintPath:
    source: SourceKind | None
    sink: Sink
    sanitized: bool = False
    reachable: bool = False
    program_tainted: bool = False   # untrusted data chooses the executable itself


@dataclass
class Finding:
    file: Path
    line: int
    pattern: str
    severity: Severity
    reason: str
    remediation: str


@dataclass
class VulnerabilityReport:
    findings: list[Finding] = field(default_factory=list)
    parse_errors: list[ParseError] = field(default_factory=list)
    files_scanned: int = 0

    def filter_by(self, severity: Severity | None) -> list[Finding]:
        return [f for f in self.findings if severity is None or f.severity == severity]

    def counts(self) -> dict:
        return {sev: sum(1 for f in self.findings if f.severity == sev) for sev in Severity}

    def merge(self, other: "VulnerabilityReport") -> None:
        self.findings += other.findings
        self.parse_errors += other.parse_errors
        self.files_scanned += other.files_scanned
