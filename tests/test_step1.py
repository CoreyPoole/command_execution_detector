import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
import pytest
from cede.file_scanner import FileScanner
from cede.rust_parser import RustParser
from cede.models import ParseError

S = pathlib.Path(__file__).resolve().parents[1] / "samples"


def test_discovers_rs_files():
    names = [p.name for p in FileScanner().discover_rs_files(S)]
    assert names == ["broken.rs", "safe.rs", "vulnerable.rs"]


def test_parses_valid_file_and_finds_functions():
    src = FileScanner().read_file(S / "vulnerable.rs")
    tree = RustParser().parse(src, S / "vulnerable.rs")
    assert len(tree.functions()) == 4


def test_comments_are_ignored():
    src = FileScanner().read_file(S / "vulnerable.rs")
    tree = RustParser().parse(src, S / "vulnerable.rs")
    calls = [tree.text(c) for fn in tree.functions() for c in tree.calls_in(fn)]
    assert not any("commented out" in c for c in calls)


def test_invalid_syntax_raises_parse_error_with_line():
    src = FileScanner().read_file(S / "broken.rs")
    with pytest.raises(ParseError) as e:
        RustParser().parse(src, S / "broken.rs")
    assert e.value.line >= 1
