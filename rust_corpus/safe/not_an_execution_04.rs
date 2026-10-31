// CEDE corpus: safe/not_an_execution_04 — comments and harmless shell-like strings
use std::process::Command;
fn main() {
    let x = "sh -c echo hello"; println!("{}", x);
}
