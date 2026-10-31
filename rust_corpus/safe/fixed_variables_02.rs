// CEDE corpus: safe/fixed_variables_02 — literal-only flow or overwrite after use
use std::process::Command;
fn main() {
    let arg = String::from("hello"); Command::new("echo").arg(arg).status().unwrap();
}
