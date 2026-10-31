import json
import sys
import pathlib

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import pytest

from cede.cli import CliApp
from cede.detection_rules import DetectionRules
from cede.models import ParseError, Severity as S
from cede.report_exporter import ReportExporter
from cede.scan_controller import ScanController


SAMPLES = pathlib.Path(__file__).resolve().parents[1] / "samples"


def findings(src):
    """Scan a snippet through the full pipeline."""
    import tempfile

    with tempfile.TemporaryDirectory() as d:
        p = pathlib.Path(d) / "t.rs"
        p.write_text(src)
        return ScanController().scan_file(p).findings


def sev(src):
    f = findings(src)
    assert len(f) == 1, f
    return f[0].severity


# ---- Scoring --------------------------------------------------------------

def test_user_input_shell_is_high():
    assert sev(
        'fn f(){ let u=env::args().nth(1).unwrap(); '
        'Command::new("sh").arg("-c").arg(u).spawn().unwrap(); }'
    ) == S.HIGH


def test_user_input_plain_arg_is_high():
    assert sev(
        'fn f(){ let u=env::args().nth(1).unwrap(); '
        'Command::new("git").arg(u).spawn().unwrap(); }'
    ) == S.HIGH


def test_env_var_plain_arg_is_medium_but_shell_is_high():
    assert sev(
        'fn f(){ let v=std::env::var("X").unwrap(); '
        'Command::new("git").arg(v).spawn().unwrap(); }'
    ) == S.MEDIUM

    assert sev(
        'fn f(){ let v=std::env::var("X").unwrap(); '
        'Command::new("sh").arg("-c").arg(v).spawn().unwrap(); }'
    ) == S.HIGH


def test_untrusted_program_name_is_high():
    f = findings(
        'fn f(){ let v=std::env::var("X").unwrap(); '
        'Command::new(v).spawn().unwrap(); }'
    )[0]

    assert f.severity == S.HIGH
    assert "chooses the program" in f.reason


def test_sanitized_is_low():
    # `sanitize` is not defined in the snippet, so the configured name is trusted.
    assert sev(
        'fn f(){ let u=env::args().nth(1).unwrap(); '
        'let c=sanitize(&u); '
        'Command::new("ls").arg(c).spawn().unwrap(); }'
    ) == S.LOW


def test_static_plain_command_not_reported_but_static_shell_is_low():
    assert findings(
        'fn f(){ Command::new("ls").arg("-la").output().unwrap(); }'
    ) == []

    assert sev(
        'fn f(){ Command::new("sh").arg("-c").arg("ls").output().unwrap(); }'
    ) == S.LOW


# ---- Controller -----------------------------------------------------------

def test_scan_file_sorted_and_complete():
    r = ScanController().scan_file(SAMPLES / "vulnerable.rs")

    assert [(f.line, f.severity) for f in r.findings] == [
        (9, S.HIGH),
        (14, S.HIGH),
        (22, S.LOW),
    ]

    assert all(
        f.reason and f.remediation and f.pattern
        for f in r.findings
    )


def test_scan_file_invalid_syntax_raises_then_fixed_file_scans():
    with pytest.raises(ParseError) as e:
        ScanController().scan_file(SAMPLES / "broken.rs")

    assert e.value.line >= 1


def test_scan_project_skips_broken_file_and_merges():
    r = ScanController().scan_project(SAMPLES)

    assert r.files_scanned == 2
    assert len(r.parse_errors) == 1
    assert r.parse_errors[0].path.name == "broken.rs"

    assert r.counts() == {
        S.HIGH: 2,
        S.MEDIUM: 0,
        S.LOW: 2,
    }

    assert [f.severity for f in r.findings] == sorted(
        (f.severity for f in r.findings),
        key=lambda s: s.rank,
    )

    assert len(r.filter_by(S.HIGH)) == 2
    assert len(r.filter_by(None)) == 4


def test_safe_file_has_no_high_or_medium():
    r = ScanController().scan_file(SAMPLES / "safe.rs")

    # safe.rs has one command fed by a real local sanitizer: exactly one LOW finding.
    assert [f.severity for f in r.findings] == [S.LOW]
    assert not any(f.severity in (S.HIGH, S.MEDIUM) for f in r.findings)


def test_custom_rules_change_results():
    # No sanitizer recognized: safe.rs becomes High.
    rules = DetectionRules(sanitizers=[])

    r = ScanController(rules).scan_file(
        SAMPLES / "safe.rs"
    )

    assert [f.severity for f in r.findings] == [S.HIGH]


def test_rules_roundtrip_and_unknown_key(tmp_path):
    p = tmp_path / "r.json"

    DetectionRules().save(p)
    assert DetectionRules.load(p) == DetectionRules()

    p.write_text('{"nope": 1}')

    with pytest.raises(ValueError):
        DetectionRules.load(p)


# ---- Exporter -------------------------------------------------------------

def test_text_and_json_export(tmp_path):
    r = ScanController().scan_project(SAMPLES)
    ex = ReportExporter()

    lines = ex.to_text(r).strip().splitlines()

    # Four findings + one skipped file + one summary.
    assert len(lines) == 4 + 1 + 1

    assert lines[0].startswith("HIGH")
    assert "Fix:" in lines[0]

    assert lines[-1].startswith(
        "Scanned 2 files · 4 findings "
        "(2 High, 0 Medium, 2 Low) · "
        "1 file(s) skipped"
    )

    data = json.loads(ex.to_json(r))

    assert data["summary"]["High"] == 2
    assert data["summary"]["Medium"] == 0
    assert data["summary"]["Low"] == 2
    assert data["summary"]["findings"] == 4

    assert len(data["findings"]) == 4
    assert len(data["parse_errors"]) == 1

    ex.save(r, tmp_path / "a.json")
    ex.save(r, tmp_path / "a.txt")

    assert (
        json.loads(
            (tmp_path / "a.json").read_text()
        )["summary"]["findings"]
        == 4
    )

    assert (
        (tmp_path / "a.txt")
        .read_text()
        .startswith("HIGH")
    )


# ---- CLI ------------------------------------------------------------------

def test_cli_output_and_exit_code(capsys):
    code = CliApp().run([
        str(SAMPLES / "vulnerable.rs")
    ])

    out = capsys.readouterr().out

    assert code == 1
    assert out.count("HIGH") == 2
    assert "vulnerable.rs:9" in out


def test_cli_min_severity_and_fail_on(capsys):
    code = CliApp().run([
        str(SAMPLES / "safe.rs"),
        "--min-severity",
        "high",
    ])

    out = capsys.readouterr().out

    assert code == 0
    assert "LOW" not in out.split("Scanned")[0]

    assert CliApp().run([
        str(SAMPLES / "vulnerable.rs"),
        "--fail-on",
        "none",
    ]) == 0


def test_cli_json_output_file_and_errors(tmp_path, capsys):
    out = tmp_path / "r.json"

    CliApp().run([
        str(SAMPLES),
        "--format",
        "json",
        "-o",
        str(out),
        "--fail-on",
        "none",
    ])

    assert (
        json.loads(
            capsys.readouterr().out
        )["summary"]["skipped_files"]
        == 1
    )

    assert out.exists()

    assert CliApp().run([
        str(tmp_path / "missing")
    ]) == 2

    assert CliApp().run([
        "--dump-default-rules"
    ]) == 0

    assert "sink_apis" in capsys.readouterr().out


# ---- Edge-case regression tests ------------------------------------------

def test_assignment_after_command_is_not_tainted():
    """An assignment after command execution must not affect that command."""
    src = """
    fn f() {
        let mut input = String::from("hello");

        Command::new("echo")
            .arg(&input)
            .output()
            .unwrap();

        input = std::env::var("UNTRUSTED").unwrap();
        println!("{}", input);
    }
    """

    assert findings(src) == []


def test_assignment_before_command_is_tainted():
    """An untrusted assignment before execution must be detected."""
    src = """
    fn f() {
        let mut input = String::from("hello");

        input = std::env::var("UNTRUSTED").unwrap();

        Command::new("echo")
            .arg(&input)
            .output()
            .unwrap();
    }
    """

    result = findings(src)

    assert len(result) == 1
    assert result[0].severity == S.MEDIUM


def test_harmless_shell_string_is_ignored():
    """A shell-like string is not a vulnerability unless executed."""
    src = """
    fn f() {
        let example = "sh -c echo hello";
        println!("{}", example);
    }
    """

    assert findings(src) == []


# ---- Cross-file isolation ---------------------------------------------------

def test_cross_file_taint_isolation(tmp_path):
    """Different source trees must not share cached taint definitions."""
    safe = tmp_path / "a_safe.rs"
    unsafe_file = tmp_path / "b_unsafe.rs"
    safe.write_text(
        'fn f(){ let x = String::from("safe"); '
        'Command::new("echo").arg(x).spawn().unwrap(); }'
    )
    unsafe_file.write_text(
        'fn f(){ let x = std::env::var("X").unwrap(); '
        'Command::new("echo").arg(x).spawn().unwrap(); }'
    )

    controller = ScanController()
    safe_result = controller.scan_file(safe)
    unsafe_result = controller.scan_file(unsafe_file)

    assert safe_result.findings == []
    assert len(unsafe_result.findings) == 1
    assert unsafe_result.findings[0].severity == S.MEDIUM

    project = controller.scan_project(tmp_path)

    assert project.files_scanned == 2
    assert len(project.findings) == 1
    assert pathlib.Path(project.findings[0].file) == unsafe_file
    assert project.findings[0].severity == S.MEDIUM


# ---- Sanitizer handling -----------------------------------------------------

def test_fake_sanitizer_does_not_lower_severity():
    """A user-defined fn that just returns its input is not a sanitizer."""
    assert sev(
        'use std::process::Command;\n'
        'fn validate(s: String) -> String {\n'
        '    s\n'
        '}\n'
        'fn main() {\n'
        '    let input = std::env::args().nth(1).unwrap();\n'
        '    let cleaned = validate(input);\n'
        '    Command::new("sh").arg("-c").arg(cleaned).spawn().unwrap();\n'
        '}\n'
    ) == S.HIGH


def test_external_configured_sanitizer_still_lowers_severity():
    """A configured external sanitizer (not defined in the file) still lowers severity."""
    assert sev(
        'use std::process::Command;\n'
        'fn main() {\n'
        '    let input = std::env::args().nth(1).unwrap();\n'
        '    let cleaned = shlex::quote(&input);\n'
        '    Command::new("sh").arg("-c").arg(cleaned).spawn().unwrap();\n'
        '}\n'
    ) == S.LOW


def test_local_sanitizer_with_real_filter_lowers_severity():
    """A local fn that actually filters its input is trusted as a sanitizer."""
    assert sev(
        'use std::process::Command;\n'
        'fn sanitize(s: &str) -> String {\n'
        '    s.chars().filter(|c| c.is_alphanumeric()).collect()\n'
        '}\n'
        'fn main() {\n'
        '    let args: Vec<String> = std::env::args().collect();\n'
        '    let dir = sanitize(&args[1]);\n'
        '    Command::new("ls").arg(dir).output().unwrap();\n'
        '}\n'
    ) == S.LOW


def test_local_identity_wrapper_is_not_a_sanitizer():
    """A local fn that only clones or converts its input is still a passthrough."""
    assert sev(
        'use std::process::Command;\n'
        'fn sanitize(s: &str) -> String {\n'
        '    s.to_string()\n'
        '}\n'
        'fn main() {\n'
        '    let args: Vec<String> = std::env::args().collect();\n'
        '    let dir = sanitize(&args[1]);\n'
        '    Command::new("ls").arg(dir).output().unwrap();\n'
        '}\n'
    ) == S.HIGH

# ---- Temporal builder state and sanitizer verification -------------------

def test_builder_argument_introduced_after_constructor_is_tainted():
    src = """
    fn f() {
        let mut cmd = Command::new("sh");
        let input = std::env::args().nth(1).unwrap();
        cmd.arg("-c");
        cmd.arg(input);
        cmd.spawn().unwrap();
    }
    """
    assert sev(src) == S.HIGH


def test_builder_argument_assignments_after_use_are_not_retroactive():
    src = """
    fn f() {
        let mut cmd = Command::new("echo");
        let mut input = String::from("safe");
        cmd.arg(&input);
        input = std::env::var("LATER").unwrap();
        cmd.spawn().unwrap();
    }
    """
    assert findings(src) == []


def test_local_logger_is_not_a_sanitizer():
    src = """
    fn sanitize(s: String) -> String {
        println!("Checking input");
        s
    }
    fn f() {
        let input = std::env::args().nth(1).unwrap();
        let result = sanitize(input);
        Command::new("sh").arg("-c").arg(result).spawn().unwrap();
    }
    """
    assert sev(src) == S.HIGH


def test_local_branching_noop_is_not_a_sanitizer():
    src = """
    fn validate(s: String) -> String {
        if s.len() > 0 { return s; }
        s
    }
    fn f() {
        let input = std::env::args().nth(1).unwrap();
        Command::new("sh").arg("-c").arg(validate(input)).spawn().unwrap();
    }
    """
    assert sev(src) == S.HIGH


def test_alias_import_command_is_detected():
    src = """
    use std::process::Command as Cmd;
    fn f() {
        let input = std::env::args().nth(1).unwrap();
        Cmd::new("sh").arg("-c").arg(input).spawn().unwrap();
    }
    """
    assert sev(src) == S.HIGH


def test_args_array_contains_shell_flag():
    src = """
    fn f() {
        let input = std::env::args().nth(1).unwrap();
        Command::new("sh").args(["-c", &input]).spawn().unwrap();
    }
    """
    assert sev(src) == S.HIGH


def test_args_array_static_shell_is_low():
    assert sev(
        'fn f(){ Command::new("sh").args(["-c", "echo hello"]).spawn().unwrap(); }'
    ) == S.LOW


def test_builder_argument_after_execution_is_ignored():
    src = """
    fn f() {
        let mut cmd = Command::new("sh");
        cmd.arg("-c");
        cmd.arg("echo safe");
        cmd.spawn().unwrap();
        let later = std::env::args().nth(1).unwrap();
        cmd.arg(later);
    }
    """
    assert sev(src) == S.LOW


def test_builder_arguments_before_execution_are_included():
    src = """
    fn f() {
        let mut cmd = Command::new("sh");
        let input = std::env::args().nth(1).unwrap();
        cmd.arg("-c");
        cmd.arg(input);
        cmd.spawn().unwrap();
    }
    """
    assert sev(src) == S.HIGH


# ---- Same-file direct caller propagation ---------------------------------

def test_untrusted_caller_arg_flows_into_command_helper():
    src = """
    fn run(command: String) {
        Command::new("sh").arg("-c").arg(command).spawn().unwrap();
    }
    fn main() {
        let input = std::env::args().nth(1).unwrap();
        run(input);
    }
    """
    assert sev(src) == S.HIGH


def test_safe_caller_arg_is_not_tainted():
    src = """
    fn run(command: String) {
        Command::new("echo").arg(command).spawn().unwrap();
    }
    fn main() { run(String::from("hello")); }
    """
    assert findings(src) == []


def test_nested_direct_helper_parameters_propagate():
    src = """
    fn execute(command: String) {
        Command::new("sh").arg("-c").arg(command).spawn().unwrap();
    }
    fn pass_along(value: String) { execute(value); }
    fn main() {
        let input = std::env::args().nth(1).unwrap();
        pass_along(input);
    }
    """
    assert sev(src) == S.HIGH


# ---- Same-file helper return values --------------------------------------

def test_direct_helper_returning_env_var_is_tainted():
    src = """
    fn load_program() -> String {
        std::env::var("PROGRAM").unwrap()
    }
    fn main() {
        Command::new(load_program()).spawn().unwrap();
    }
    """
    assert sev(src) == S.HIGH


def test_helper_returning_parameter_keeps_taint():
    src = """
    fn identity(s: String) -> String { s }
    fn main() {
        let input = std::env::args().nth(1).unwrap();
        Command::new("sh").arg("-c").arg(identity(input)).spawn().unwrap();
    }
    """
    assert sev(src) == S.HIGH


def test_helper_returning_constant_does_not_taint_from_unused_input():
    src = """
    fn constant(_value: String) -> String { String::from("hello") }
    fn main() {
        let untrusted = std::env::args().nth(1).unwrap();
        Command::new("echo").arg(constant(untrusted)).spawn().unwrap();
    }
    """
    assert findings(src) == []


def test_helper_returning_local_variable_keeps_taint():
    src = """
    fn identity(s: String) -> String {
        let value = s;
        value
    }
    fn main() {
        let input = std::env::args().nth(1).unwrap();
        Command::new("sh").arg("-c").arg(identity(input)).spawn().unwrap();
    }
    """
    assert sev(src) == S.HIGH


def test_reused_command_builder_reports_each_execution():
    src = """
    fn f() {
        let mut cmd = Command::new("sh");
        cmd.arg("-c");
        cmd.arg("echo okay");
        cmd.spawn().unwrap();
        let later = std::env::args().nth(1).unwrap();
        cmd.arg(later);
        cmd.spawn().unwrap();
    }
    """
    result = findings(src)
    assert len(result) == 2
    assert [f.severity for f in result] == [S.HIGH, S.LOW]


def test_reused_command_builder_does_not_confuse_first_execution():
    src = """
    fn f() {
        let mut cmd = Command::new("echo");
        cmd.arg("safe");
        cmd.spawn().unwrap();
        let later = std::env::var("AFTER").unwrap();
        cmd.arg(later);
        cmd.spawn().unwrap();
    }
    """
    result = findings(src)
    assert len(result) == 1
    assert result[0].severity == S.MEDIUM


# ---- CLI output and rules validation regressions -------------------------

def test_cli_json_output_respects_format_even_with_txt_extension(tmp_path):
    output = tmp_path / "report.txt"
    code = CliApp().run([
        str(SAMPLES / "safe.rs"), "--format", "json",
        "-o", str(output), "--fail-on", "none",
    ])
    assert code == 0
    assert json.loads(output.read_text())["summary"]["files_scanned"] == 1


def test_cli_rejects_non_rust_file(tmp_path, capsys):
    file = tmp_path / "notes.txt"
    file.write_text("hello")
    assert CliApp().run([str(file)]) == 2
    assert "not a Rust" in capsys.readouterr().err


def test_cli_handles_unwritable_output(tmp_path, capsys):
    assert CliApp().run([
        str(SAMPLES / "safe.rs"),
        "-o", str(tmp_path / "no-such-dir" / "report.txt"),
        "--fail-on", "none",
    ]) == 2
    assert "cannot save report" in capsys.readouterr().err


def test_invalid_rules_are_rejected_with_clear_error(tmp_path, capsys):
    rules = tmp_path / "bad_rules.json"
    rules.write_text('{"sources": {"foo": "UnknownSource"}}')
    assert CliApp().run([str(SAMPLES / "safe.rs"), "--rules", str(rules)]) == 2
    assert "cannot load rules" in capsys.readouterr().err
    rules.write_text('{"sanitizers": "sanitize"}')
    assert CliApp().run([str(SAMPLES / "safe.rs"), "--rules", str(rules)]) == 2


# ---- Conservative branch and lexical scope handling ---------------------

def test_if_assignment_may_taint_command():
    src = """
    fn f() {
        let mut cmd = String::from("safe");
        if std::env::args().len() > 1 {
            cmd = std::env::args().nth(1).unwrap();
        }
        Command::new("sh").arg("-c").arg(cmd).spawn().unwrap();
    }
    """
    assert sev(src) == S.HIGH


def test_match_assignment_may_taint_command():
    src = """
    fn f() {
        let mut cmd = String::from("safe");
        match std::env::var("X") {
            Ok(value) => { cmd = value; }
            Err(_) => {}
        };
        Command::new("sh").arg("-c").arg(cmd).spawn().unwrap();
    }
    """
    assert sev(src) == S.HIGH


def test_unconditional_overwrite_after_branch_clears_taint():
    src = """
    fn f() {
        let mut cmd = String::from("safe");
        if true { cmd = std::env::var("X").unwrap(); }
        cmd = String::from("safe again");
        Command::new("echo").arg(cmd).spawn().unwrap();
    }
    """
    assert findings(src) == []


def test_inner_block_shadow_does_not_escape():
    src = """
    fn f() {
        let input = String::from("safe");
        {
            let input = std::env::args().nth(1).unwrap();
            println!("{}", input);
        }
        Command::new("echo").arg(input).spawn().unwrap();
    }
    """
    assert findings(src) == []


# ---- Cross-file Rust module propagation ----------------------------------

def test_project_module_argument_taint(tmp_path):
    (tmp_path / "main.rs").write_text(
        'mod runner;\nfn main(){ let input = std::env::args().nth(1).unwrap(); '
        'runner::execute(input); }'
    )
    (tmp_path / "runner.rs").write_text(
        'pub fn execute(cmd: String){ '
        'std::process::Command::new("sh").arg("-c").arg(cmd).spawn().unwrap(); }'
    )
    report = ScanController().scan_project(tmp_path)
    assert report.files_scanned == 2
    assert len(report.findings) == 1
    assert report.findings[0].severity == S.HIGH
    assert report.findings[0].file.name == "runner.rs"


def test_project_explicit_import_propagates_argument(tmp_path):
    (tmp_path / "main.rs").write_text(
        'mod runner;\nuse crate::runner::execute;\n'
        'fn main(){ execute(std::env::var("CMD").unwrap()); }'
    )
    (tmp_path / "runner.rs").write_text(
        'pub fn execute(cmd: String){ '
        'std::process::Command::new("echo").arg(cmd).spawn().unwrap(); }'
    )
    report = ScanController().scan_project(tmp_path)
    assert len(report.findings) == 1
    assert report.findings[0].severity == S.MEDIUM


def test_project_return_value_taint(tmp_path):
    (tmp_path / "main.rs").write_text(
        'mod runner;\nfn main(){ '
        'std::process::Command::new(runner::load_program()).spawn().unwrap(); }'
    )
    (tmp_path / "runner.rs").write_text(
        'pub fn load_program() -> String { std::env::var("PROGRAM").unwrap() }'
    )
    report = ScanController().scan_project(tmp_path)
    assert len(report.findings) == 1
    assert report.findings[0].severity == S.HIGH


def test_project_does_not_confuse_unrelated_modules(tmp_path):
    (tmp_path / "main.rs").write_text(
        'mod a;\nmod b;\nfn main(){ '
        'a::execute(std::env::var("CMD").unwrap()); }'
    )
    (tmp_path / "a.rs").write_text(
        'pub fn execute(cmd: String){ println!("{}", cmd); }'
    )
    (tmp_path / "b.rs").write_text(
        'pub fn execute(cmd: String){ '
        'std::process::Command::new("echo").arg(cmd).spawn().unwrap(); }'
    )
    report = ScanController().scan_project(tmp_path)
    assert report.findings == []
