// CEDE corpus: safe/not_an_execution_06 — comments and harmless shell-like strings
use std::process::Command;
fn main() {
    let x = "powershell -Command echo"; println!("{}", x);
}
