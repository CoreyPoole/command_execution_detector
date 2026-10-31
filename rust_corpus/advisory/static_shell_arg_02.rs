// CEDE corpus: advisory/static_shell_arg_02 — shell with only fixed script
use std::process::Command;
fn main() {
    Command::new("bash").arg("-c").arg("echo hello").status().unwrap();
}
