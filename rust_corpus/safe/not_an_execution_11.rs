// CEDE corpus: safe/not_an_execution_11 — comments and harmless shell-like strings
use std::process::Command;
fn main() {
    let mut words = vec!["sh", "-c"]; words.push("safe");
}
