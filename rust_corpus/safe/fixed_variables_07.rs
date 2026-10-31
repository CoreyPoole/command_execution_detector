// CEDE corpus: safe/fixed_variables_07 — literal-only flow or overwrite after use
use std::process::Command;
fn main() {
    let name = "status"; Command::new("git").arg(name).spawn().unwrap();
}
