// CEDE corpus: advisory/static_shell_arg_05 — shell with only fixed script
use std::process::Command;
fn main() {
    Command::new("powershell").arg("-Command").arg("echo hello").status().unwrap();
}
