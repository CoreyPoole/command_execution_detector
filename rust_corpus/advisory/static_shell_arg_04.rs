// CEDE corpus: advisory/static_shell_arg_04 — shell with only fixed script
use std::process::Command;
fn main() {
    Command::new("cmd.exe").arg("/C").arg("echo hello").status().unwrap();
}
