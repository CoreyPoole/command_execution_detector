// CEDE corpus: safe/fixed_variables_06 — literal-only flow or overwrite after use
use std::process::Command;
fn main() {
    let mut input = String::from("safe"); Command::new("echo").arg(&input).output().unwrap(); input = std::env::var("AFTER").unwrap();
}
