// CEDE corpus: advisory/static_shell_args_05 — shell args array with fixed script
use std::process::Command;
fn main() {
    Command::new("powershell").args(["-Command", "echo hello"]).output().unwrap();
}
