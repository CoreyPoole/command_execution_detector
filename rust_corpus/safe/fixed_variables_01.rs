// CEDE corpus: safe/fixed_variables_01 — literal-only flow or overwrite after use
use std::process::Command;
fn main() {
    let cmd = String::from("git"); Command::new(cmd).arg("status").status().unwrap();
}
