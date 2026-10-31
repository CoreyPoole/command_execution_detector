// CEDE corpus: advisory/static_shell_arg_03 — shell with only fixed script
use std::process::Command;
fn main() {
    Command::new("cmd").arg("/C").arg("echo hello").status().unwrap();
}
