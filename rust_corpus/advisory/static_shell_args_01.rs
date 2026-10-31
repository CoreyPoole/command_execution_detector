// CEDE corpus: advisory/static_shell_args_01 — shell args array with fixed script
use std::process::Command;
fn main() {
    Command::new("sh").args(["-c", "echo hello"]).output().unwrap();
}
