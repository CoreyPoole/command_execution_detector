// CEDE corpus: advisory/static_shell_args_04 — shell args array with fixed script
use std::process::Command;
fn main() {
    Command::new("cmd.exe").args(["/C", "echo hello"]).output().unwrap();
}
