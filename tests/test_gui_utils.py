from pathlib import Path
from cede.gui_utils import source_context


def test_gui_source_context_highlights_line(tmp_path):
    file = tmp_path / "test.rs"
    file.write_text("one\ntwo\nthree\nfour\nfive\n")
    out = source_context(file, 3, radius=1)
    assert "     2 | two" in out
    assert ">    3 | three" in out
    assert "     4 | four" in out
    assert "one" not in out


def test_gui_source_context_handles_missing_file(tmp_path):
    assert "no longer available" in source_context(tmp_path / "missing.rs", 2)


def test_cancel_stops_project_after_first_processed_file(tmp_path):
    from cede.scan_controller import ScanController
    for i in range(5):
        (tmp_path / f"{i}.rs").write_text(
            'fn f(){ std::process::Command::new("ls").spawn().unwrap(); }'
        )
    state = {"calls": 0}
    def cancelled():
        state["calls"] += 1
        return state["calls"] > 7
    report = ScanController().scan_project(tmp_path, cancel=cancelled)
    assert report.files_scanned < 5
