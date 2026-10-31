// CEDE corpus: advisory/static_shell_args_06 — shell args array with fixed script
use std::process::Command;
fn main() {
    Command::new("/bin/sh").args(["-c", "echo hello"]).output().unwrap();
}
