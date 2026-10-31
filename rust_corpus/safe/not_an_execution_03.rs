// CEDE corpus: safe/not_an_execution_03 — comments and harmless shell-like strings
use std::process::Command;
fn main() {
    let doc = r#"Command::new("bash").arg("-c")"#; println!("{}", doc);
}
