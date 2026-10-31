// CEDE corpus: safe/not_an_execution_05 — comments and harmless shell-like strings
use std::process::Command;
fn main() {
    let x = "cmd /C dir"; println!("{}", x);
}
