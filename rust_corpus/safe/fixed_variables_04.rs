// CEDE corpus: safe/fixed_variables_04 — literal-only flow or overwrite after use
use std::process::Command;
fn main() {
    let mut value = String::from("before"); value = String::from("after"); Command::new("echo").arg(value).status().unwrap();
}
