"""Test CEDE on complete folders with multiple Rust source files.

Sample sources must never be executed; these tests only parse them.
"""
import json
from pathlib import Path
import pytest
from cede.scan_controller import ScanController

ROOT = Path(__file__).resolve().parents[1] / "rust_projects"
PROJECTS = json.loads((ROOT / "manifest.json").read_text(encoding="utf-8"))["projects"]


@pytest.mark.parametrize("case", PROJECTS, ids=lambda case: case["name"])
def test_multi_file_rust_project(case):
    folder = Path(__file__).resolve().parents[1] / case["directory"]
    report = ScanController().scan_project(folder)
    actual = [{"file": f.file.relative_to(folder).as_posix(),
               "severity": f.severity.value} for f in report.findings]
    assert report.files_scanned == case["files_scanned"]
    assert len(report.parse_errors) == case["parse_errors"]
    assert actual == case["findings"], case["description"]


def test_multi_file_project_inventory():
    assert len(PROJECTS) >= 20
    assert len({case["name"] for case in PROJECTS}) == len(PROJECTS)
    folders = {p.name for p in ROOT.iterdir() if p.is_dir()}
    assert folders == {case["name"] for case in PROJECTS}
    for case in PROJECTS:
        folder = Path(__file__).resolve().parents[1] / case["directory"]
        rust_files = list(folder.rglob("*.rs"))
        assert rust_files, case["name"]
        assert len(rust_files) == case["files_scanned"]
