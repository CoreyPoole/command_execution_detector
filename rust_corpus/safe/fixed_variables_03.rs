// CEDE corpus: safe/fixed_variables_03 — literal-only flow or overwrite after use
use std::process::Command;
fn main() {
    let cmd = "ls"; Command::new(cmd).arg("-la").status().unwrap();
}
