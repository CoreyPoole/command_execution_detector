// CEDE corpus: advisory/static_shell_args_03 — shell args array with fixed script
use std::process::Command;
fn main() {
    Command::new("cmd").args(["/C", "echo hello"]).output().unwrap();
}
