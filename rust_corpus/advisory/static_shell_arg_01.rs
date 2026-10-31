// CEDE corpus: advisory/static_shell_arg_01 — shell with only fixed script
use std::process::Command;
fn main() {
    Command::new("sh").arg("-c").arg("echo hello").status().unwrap();
}
