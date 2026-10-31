"""Run a deliberately small, deterministic labeled CEDE fixture benchmark.

The benchmark is a regression/precision smoke test, not an external
evaluation of real Rust programs or a security guarantee.
"""
import argparse
import json
from pathlib import Path
from .scan_controller import ScanController
from .models import Severity

DATA = Path(__file__).resolve().parents[1] / "benchmarks"


def evaluate(directory: Path = DATA) -> dict:
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    counts = {"tp": 0, "fp": 0, "tn": 0, "fn": 0}
    mismatches = []
    controller = ScanController()
    for example in manifest:
        path = directory / "fixtures" / example["file"]
        report = controller.scan_file(path)
        observed = report.findings[0].severity.value if report.findings else None
        expected = example["expected_severity"]
        true_positive = example["actionable"]
        predicted_positive = any(
            finding.severity in (Severity.HIGH, Severity.MEDIUM)
            for finding in report.findings
        )
        cell = ("tp" if true_positive else "fp") if predicted_positive else (
            "fn" if true_positive else "tn"
        )
        counts[cell] += 1
        if observed != expected:
            mismatches.append({
                "file": example["file"], "expected": expected, "observed": observed
            })
    precision_den = counts["tp"] + counts["fp"]
    recall_den = counts["tp"] + counts["fn"]
    return {
        "cases": len(manifest), **counts,
        "precision": counts["tp"] / precision_den if precision_den else 1.0,
        "recall": counts["tp"] / recall_den if recall_den else 1.0,
        "severity_mismatches": mismatches,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description="Evaluate the curated CEDE fixture benchmark")
    parser.add_argument("--directory", type=Path, default=DATA)
    args = parser.parse_args(argv)
    result = evaluate(args.directory)
    print(json.dumps(result, indent=2))
    return 1 if result["severity_mismatches"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
