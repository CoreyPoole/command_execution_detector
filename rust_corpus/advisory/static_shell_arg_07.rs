// CEDE corpus: advisory/static_shell_arg_07 — shell with only fixed script
use std::process::Command;
fn main() {
    Command::new("/bin/bash").arg("-c").arg("echo hello").status().unwrap();
}
