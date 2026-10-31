// CEDE corpus: safe/literal_direct_08 — fixed executable and literal argument
use std::process::Command;
fn main() {
    Command::new("rustc").arg("--version").status().unwrap();
}
