"""Verify manifest comparisons without requiring a graphical display."""
import json
from pathlib import Path

import pytest

from cede.testing_dashboard import evaluate_suite

ROOT = Path(__file__).resolve().parents[1]


def make_suite(tmp_path, kind, entries, sources):
    root = tmp_path / kind
    root.mkdir()
    for filename, content in sources.items():
        path = root / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf-8")
    key = "cases" if kind == "rust_corpus" else "projects"
    (root / "manifest.json").write_text(json.dumps({key: entries}), encoding="utf-8")
    return root


def test_existing_single_file_corpus():
    result = evaluate_suite(ROOT / "rust_corpus")
    assert result.total == 151
    assert (result.passed, result.failed, result.skipped) == (139, 0, 12)
    assert result.processed == 151
    assert not result.cancelled


def test_existing_independent_project_corpus():
    result = evaluate_suite(ROOT / "rust_projects")
    assert result.total == 30
    assert (result.passed, result.failed, result.skipped) == (30, 0, 0)


def test_mismatch_and_expected_parse_error(tmp_path):
    root = make_suite(tmp_path, "rust_corpus", [
        {"path": "rust_corpus/safe.rs", "expected": "High"},
        {"path": "rust_corpus/broken.rs", "expected": "ParseError"},
    ], {
        "safe.rs": 'fn f(){ std::process::Command::new("echo").arg("safe").status().unwrap(); }',
        "broken.rs": "fn broken( { let x = ; }",
    })
    result = evaluate_suite(root)
    assert (result.passed, result.failed, result.skipped) == (0, 1, 1)
    assert result.cases[0].actual == "None"
    assert result.cases[0].status == "FAIL"
    assert result.cases[1].status == "SKIP"


def test_unexpected_parse_error_is_failure(tmp_path):
    root = make_suite(tmp_path, "rust_corpus", [
        {"path": "rust_corpus/broken.rs", "expected": "None"}
    ], {"broken.rs": "fn broken( {"})
    result = evaluate_suite(root)
    assert (result.failed, result.skipped) == (1, 0)
    assert result.cases[0].actual == "ParseError"


def test_missing_file_is_failure(tmp_path):
    root = make_suite(tmp_path, "rust_corpus", [
        {"path": "rust_corpus/gone.rs", "expected": "None"}
    ], {})
    result = evaluate_suite(root)
    assert result.failed == 1
    assert result.cases[0].status == "FAIL"


def test_manifest_path_cannot_escape_suite(tmp_path):
    root = make_suite(tmp_path, "rust_corpus", [
        {"path": "rust_corpus/../private.rs", "expected": "None"}
    ], {})
    result = evaluate_suite(root)
    assert result.failed == 1
    assert "Invalid rust_corpus manifest path" in result.cases[0].details


def test_cancellation_does_not_mark_unrun_cases_passed(tmp_path):
    entries = [{"path": f"rust_corpus/{i}.rs", "expected": "None"}
               for i in range(4)]
    content = 'fn f(){ std::process::Command::new("echo").status().unwrap(); }'
    root = make_suite(tmp_path, "rust_corpus", entries,
                      {f"{i}.rs": content for i in range(4)})
    processed = []
    result = evaluate_suite(
        root,
        progress=lambda n, total, name: processed.append((n, total, name)),
        cancel=lambda: len(processed) >= 2,
    )
    assert result.cancelled
    assert result.total == 4
    assert result.processed == 2
    assert result.passed == 2
    assert [entry[0] for entry in processed] == [1, 2]


def test_invalid_or_empty_manifest_rejected(tmp_path):
    root = tmp_path / "broken"
    root.mkdir()
    with pytest.raises(ValueError, match="manifest.json"):
        evaluate_suite(root)
    (root / "manifest.json").write_text('{"cases": []}')
    with pytest.raises(ValueError, match="no cases"):
        evaluate_suite(root)


def test_project_detects_unexpected_finding(tmp_path):
    root = make_suite(tmp_path, "rust_projects", [{
        "name": "mini", "directory": "rust_projects/mini",
        "files_scanned": 1, "parse_errors": 0, "findings": [],
    }], {
        "mini/main.rs": (
            'fn f(){ std::process::Command::new("sh").arg("-c")'
            '.arg("echo hi").spawn().unwrap(); }'
        ),
    })
    result = evaluate_suite(root)
    assert result.failed == 1
    assert "Low" in result.cases[0].actual
    assert result.cases[0].expected == "None"


def test_project_detects_file_count_mismatch(tmp_path):
    root = make_suite(tmp_path, "rust_projects", [{
        "name": "mini", "directory": "rust_projects/mini",
        "files_scanned": 2, "parse_errors": 0, "findings": [],
    }], {"mini/main.rs": 'fn main(){ println!("okay"); }'})
    result = evaluate_suite(root)
    assert result.failed == 1
    assert "Files scanned: 1 (expected 2)" in result.cases[0].details
