// CEDE corpus: safe/fixed_variables_05 — literal-only flow or overwrite after use
use std::process::Command;
fn main() {
    let input = String::from("safe"); Command::new("echo").arg(&input).output().unwrap();
}
