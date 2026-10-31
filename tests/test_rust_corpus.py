"""Run every labeled Rust corpus fixture through the complete CEDE pipeline.

Do NOT execute these Rust samples. Several show unsafe command-execution patterns
and are intentionally only meant for static parsing and analysis.
"""
import json
from collections import Counter
from pathlib import Path

import pytest
from cede.models import ParseError
from cede.scan_controller import ScanController

ROOT = Path(__file__).resolve().parents[1] / "rust_corpus"
MANIFEST = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))
CASES = MANIFEST["cases"]


@pytest.mark.parametrize("case", CASES, ids=lambda case: case["path"])
def test_labeled_rust_corpus(case):
    path = Path(__file__).resolve().parents[1] / case["path"]
    assert path.is_file()
    if case["expected"] == "ParseError":
        with pytest.raises(ParseError):
            ScanController().scan_file(path)
        return
    report = ScanController().scan_file(path)
    observed = [f.severity.value for f in report.findings]
    expected = [] if case["expected"] == "None" else [case["expected"]]
    assert observed == expected, (
        f"{case['path']}: expected {expected}, observed {observed}"
    )


def test_corpus_inventory_and_distribution():
    assert MANIFEST["schema_version"] == 1
    names = [case["path"] for case in CASES]
    assert len(names) == len(set(names))
    tracked = {
        path.relative_to(ROOT.parent).as_posix()
        for path in ROOT.rglob("*.rs")
    }
    assert tracked == set(names), "Every .rs fixture must be labeled in manifest.json"
    counts = Counter(case["expected"] for case in CASES)
    assert len(CASES) >= 120
    assert counts["High"] >= 20
    assert counts["Medium"] >= 20
    assert counts["Low"] >= 15
    assert counts["None"] >= 20
    assert counts["ParseError"] >= 10
