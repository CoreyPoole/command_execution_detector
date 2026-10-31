// CEDE corpus: safe/not_an_execution_10 — comments and harmless shell-like strings
use std::process::Command;
fn main() {
    let code = "std::process::Command::new"; println!("{}", code);
}
