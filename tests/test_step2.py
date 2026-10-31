import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from cede.rust_parser import RustParser
from cede.sink_detector import SinkDetector

S = pathlib.Path(__file__).resolve().parents[1] / "samples"


def sinks_for(src):
    return SinkDetector().find_sinks(RustParser().parse(src, "t.rs"))


def test_sample_file_sinks():
    p = S / "vulnerable.rs"
    sinks = sinks_for(p.read_text())
    apis = [s.api for s in sinks]
    assert len(sinks) == 4        
    assert 'Command::new("sh").arg("-c").arg(user).spawn()' in apis
    assert not any("commented out" in a for a in apis)


def test_shell_invocation_flag():
    s = sinks_for('fn f(u:String){ Command::new("sh").arg("-c").arg(u).spawn().unwrap(); }')[0]
    assert s.is_shell_invocation and s.methods == ["arg", "arg", "spawn", "unwrap"]
    assert len(s.arg_nodes) == 2


def test_plain_command_is_not_shell():
    s = sinks_for('fn f(){ Command::new("git").arg("status").output().unwrap(); }')[0]
    assert not s.is_shell_invocation


def test_comments_and_docs_ignored():
    src = '/// Command::new("sh")\nfn f(){ // Command::new("rm")\n let a = 1; }'
    assert sinks_for(src) == []


def test_line_numbers():
    s = sinks_for('fn f(){\n\n  Command::new("ls").spawn().unwrap();\n}')[0]
    assert s.line == 3


def test_bare_shell_string():
    sinks = sinks_for('fn f(){ let x = "cmd /C"; }')
    assert len(sinks) == 0

