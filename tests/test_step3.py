import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
from cede.models import SourceKind as K
from cede.rust_parser import RustParser
from cede.sink_detector import SinkDetector
from cede.taint_analyzer import TaintAnalyzer

S = pathlib.Path(__file__).resolve().parents[1] / "samples"


def paths(src):
    tree = RustParser().parse(src, "t.rs")
    return TaintAnalyzer().trace(tree, SinkDetector().find_sinks(tree))


def one(src):
    p = paths(src)
    assert len(p) == 1
    return p[0]


def test_stdin_to_shell_sample_file():
    p = S / "vulnerable.rs"
    tree = RustParser().parse(p.read_text(), p)
    res = {t.sink.line: t for t in TaintAnalyzer().trace(tree, SinkDetector().find_sinks(tree))}
    assert res[9].source == K.USER_INPUT and res[9].reachable and not res[9].sanitized
    assert res[14].source == K.ENV_VAR and res[14].reachable
    assert not res[18].reachable and res[18].source is None      # Command::new("git").arg("status")
    assert 23 not in res                                # bare "sh -c" string


def test_literals_only_is_clean():
    t = one('fn f(){ Command::new("ls").arg("-la").output().unwrap(); }')
    assert not t.reachable and t.source is None


def test_sanitizer_marks_path_sanitized():
    t = one('fn f(){ let mut u=String::new(); io::stdin().read_line(&mut u).unwrap();'
            ' let c = sanitize(&u); Command::new("sh").arg("-c").arg(c).spawn().unwrap(); }')
    assert t.source == K.USER_INPUT and t.reachable and t.sanitized


def test_unsanitized_wins_over_sanitized():
    t = one('fn f(){ let a = env::args().nth(1).unwrap(); let b = std::env::var("X").unwrap();'
            ' Command::new("echo").arg(shell_escape::escape(a)).arg(b).spawn().unwrap(); }')
    assert t.source == K.ENV_VAR and not t.sanitized


def test_env_args_collect_and_index():
    t = one('fn f(){ let a: Vec<String> = std::env::args().collect(); Command::new(&a[1]).spawn().unwrap(); }')
    assert t.source == K.USER_INPUT and t.reachable


def test_format_macro_positional_and_inline():
    t1 = one('fn f(){ let u = std::env::args().nth(1).unwrap(); let c = format!("ls {}", u);'
             ' Command::new("sh").arg("-c").arg(c).spawn().unwrap(); }')
    t2 = one('fn f(){ let u = std::env::args().nth(1).unwrap(); let c = format!("ls {u}");'
             ' Command::new("sh").arg("-c").arg(c).spawn().unwrap(); }')
    assert t1.source == t2.source == K.USER_INPUT


def test_file_and_network_sources():
    f = one('fn f(){ let cfg = std::fs::read_to_string("x").unwrap(); Command::new(cfg).spawn().unwrap(); }')
    n = one('fn f(){ let d = reqwest::blocking::get("http://h").unwrap().text().unwrap(); Command::new(d).spawn().unwrap(); }')
    assert f.source == K.FILE and n.source == K.NETWORK


def test_most_dangerous_source_wins():
    t = one('fn f(){ let a = std::fs::read_to_string("x").unwrap(); let b = env::args().nth(1).unwrap();'
            ' Command::new("sh").arg("-c").arg(a).arg(b).spawn().unwrap(); }')
    assert t.source == K.USER_INPUT


def test_mutator_push_str():
    t = one('fn f(){ let mut u=String::new(); io::stdin().read_line(&mut u).unwrap();'
            ' let mut c = String::from("ls "); c.push_str(&u); Command::new("sh").arg("-c").arg(c).spawn().unwrap(); }')
    assert t.source == K.USER_INPUT


def test_command_built_in_pieces_is_linked():
    src = ('fn f(){ let u = env::args().nth(1).unwrap(); let mut c = Command::new("sh");'
           ' c.arg("-c"); c.arg(u); c.spawn().unwrap(); }')
    tree = RustParser().parse(src, "t.rs")
    sinks = SinkDetector().find_sinks(tree)
    assert sinks[0].is_shell_invocation                 # -c flag found via variable
    assert TaintAnalyzer().trace(tree, sinks)[0].source == K.USER_INPUT


def test_untainted_variable_is_clean():
    t = one('fn f(){ let c = String::from("status"); Command::new("git").arg(c).output().unwrap(); }')
    assert not t.reachable
