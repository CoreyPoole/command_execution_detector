// CEDE corpus: safe/not_an_execution_01 — comments and harmless shell-like strings
use std::process::Command;
fn main() {
    let example = "Command::new(\"sh\").arg(\"-c\")"; println!("{}", example);
}
