// CEDE corpus: advisory/static_shell_args_02 — shell args array with fixed script
use std::process::Command;
fn main() {
    Command::new("bash").args(["-c", "echo hello"]).output().unwrap();
}
