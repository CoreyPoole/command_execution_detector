// CEDE corpus: safe/not_an_execution_07 — comments and harmless shell-like strings
use std::process::Command;
fn main() {
    let x = "Command::new"; println!("{}", x);
}
