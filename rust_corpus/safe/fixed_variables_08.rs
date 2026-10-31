// CEDE corpus: safe/fixed_variables_08 — literal-only flow or overwrite after use
use std::process::Command;
fn main() {
    let input = std::env::var("CMD").unwrap(); let cleaned = "fixed"; println!("{}", input); Command::new("echo").arg(cleaned).status().unwrap();
}
