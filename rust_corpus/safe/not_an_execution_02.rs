// CEDE corpus: safe/not_an_execution_02 — comments and harmless shell-like strings
use std::process::Command;
fn main() {
    // Command::new("sh").arg("-c").spawn();
 let text = "not executed"; println!("{}", text);
}
