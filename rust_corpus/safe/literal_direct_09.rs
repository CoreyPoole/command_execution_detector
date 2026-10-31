// CEDE corpus: safe/literal_direct_09 — fixed executable and literal argument
use std::process::Command;
fn main() {
    Command::new("cargo").arg("--version").status().unwrap();
}
