// CEDE corpus: advisory/static_shell_arg_06 — shell with only fixed script
use std::process::Command;
fn main() {
    Command::new("/bin/sh").arg("-c").arg("echo hello").status().unwrap();
}
