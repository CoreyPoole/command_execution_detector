"""Manifest-aware regression evaluation for CEDE's Rust test suites.

Each case is scanned independently. The Rust sources are never executed.
Passing a curated suite confirms expected behavior on these examples,
not real-world vulnerability-detection accuracy.
"""
from __future__ import annotations

import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

from .detection_rules import DetectionRules
from .models import ParseError
from .scan_controller import ScanController

EXPECTED = {"High", "Medium", "Low", "None", "ParseError"}


@dataclass(frozen=True)
class CaseResult:
    name: str
    expected: str
    actual: str
    status: str                  # PASS, FAIL, or SKIP (expected invalid syntax)
    details: str = ""


@dataclass
class SuiteResult:
    suite: str
    total: int
    cases: list[CaseResult]
    cancelled: bool = False

    @property
    def passed(self) -> int:
        return sum(c.status == "PASS" for c in self.cases)

    @property
    def failed(self) -> int:
        return sum(c.status == "FAIL" for c in self.cases)

    @property
    def skipped(self) -> int:
        return sum(c.status == "SKIP" for c in self.cases)

    @property
    def processed(self) -> int:
        return len(self.cases)


def _inside_suite(root: Path, manifest_path: str, prefix: str) -> Path:
    """Resolve manifest paths without allowing absolute or parent traversal."""
    relative = Path(manifest_path)
    if (relative.is_absolute() or not relative.parts or
            relative.parts[0] != prefix or
            ".." in relative.parts or len(relative.parts) < 2):
        raise ValueError(f"Invalid {prefix} manifest path: {manifest_path}")
    result = (root / Path(*relative.parts[1:])).resolve()
    if not result.is_relative_to(root.resolve()):
        raise ValueError(f"Path outside test suite: {manifest_path}")
    return result


def _read_manifest(root: Path):
    manifest_file = root / "manifest.json"
    try:
        document = json.loads(manifest_file.read_text(encoding="utf-8"))
    except (OSError, ValueError) as exc:
        raise ValueError(
            f"Select a rust_corpus or rust_projects folder containing manifest.json: {exc}"
        ) from exc
    if not isinstance(document, dict):
        raise ValueError("Invalid manifest: expected a JSON object")
    if isinstance(document.get("cases"), list) and "projects" not in document:
        return "Rust files", "rust_corpus", document["cases"]
    if isinstance(document.get("projects"), list) and "cases" not in document:
        return "Rust projects", "rust_projects", document["projects"]
    raise ValueError("Manifest must contain exactly one of 'cases' or 'projects'")


def _compare_file(root: Path, item: dict, controller: ScanController) -> CaseResult:
    name = item["path"]
    expected = item["expected"]
    if expected not in EXPECTED:
        raise ValueError(f"Invalid expected severity for {name}: {expected}")
    target = _inside_suite(root, name, "rust_corpus")
    try:
        report = controller.scan_file(target)
        observed = [finding.severity.value for finding in report.findings]
    except ParseError as exc:
        if expected == "ParseError":
            return CaseResult(name, "ParseError", "ParseError", "SKIP",
                              f"Intentionally malformed Rust: {exc.message}")
        return CaseResult(name, expected, "ParseError", "FAIL",
                          f"Unexpected syntax error at line {exc.line}: {exc.message}")

    actual = ", ".join(observed) if observed else "None"
    match = observed == ([] if expected == "None" else [expected])
    return CaseResult(name, expected, actual, "PASS" if match else "FAIL",
                      item.get("topic", ""))


def _findings_label(entries: list[tuple[str, str]]) -> str:
    return "; ".join(f"{severity} — {path}" for path, severity in entries) or "None"


def _compare_project(root: Path, item: dict, controller: ScanController) -> CaseResult:
    name = item["name"]
    directory = _inside_suite(root, item["directory"], "rust_projects")
    report = controller.scan_project(directory)
    found = sorted(
        (finding.file.relative_to(directory).as_posix(), finding.severity.value)
        for finding in report.findings
    )
    expected = sorted((entry["file"].replace("\\", "/"), entry["severity"])
                      for entry in item["findings"])
    expected_errors = item.get("parse_errors", 0)
    match = (Counter(found) == Counter(expected)
             and report.files_scanned == item["files_scanned"]
             and len(report.parse_errors) == expected_errors)
    detail = (
        f"{item.get('description', '')}\n"
        f"Files scanned: {report.files_scanned} (expected {item['files_scanned']}); "
        f"parse errors: {len(report.parse_errors)} (expected {expected_errors})"
    )
    return CaseResult(name, _findings_label(expected), _findings_label(found),
                      "PASS" if match else "FAIL", detail)


def evaluate_suite(
    root: Path,
    rules: DetectionRules | None = None,
    progress: Callable[[int, int, str], None] | None = None,
    cancel: Callable[[], bool] | None = None,
) -> SuiteResult:
    """Evaluate each manifest entry independently, never as one giant project."""
    root = Path(root).resolve()
    name, kind, items = _read_manifest(root)
    if not items:
        raise ValueError("Test suite manifest contains no cases")
    controller = ScanController(rules)
    result = SuiteResult(name, len(items), [])
    for index, item in enumerate(items, 1):
        if cancel is not None and cancel():
            result.cancelled = True
            break
        try:
            case = (_compare_file(root, item, controller) if kind == "rust_corpus"
                    else _compare_project(root, item, controller))
        except (OSError, ValueError, KeyError, TypeError) as exc:
            label = str(item.get("path", item.get("name", f"case {index}")))
            case = CaseResult(label, "Valid manifest case", type(exc).__name__,
                              "FAIL", str(exc))
        result.cases.append(case)
        if progress:
            progress(index, len(items), case.name)
    return result
