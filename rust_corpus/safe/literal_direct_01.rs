// CEDE corpus: safe/literal_direct_01 — fixed executable and literal argument
use std::process::Command;
fn main() {
    Command::new("git").arg("status").status().unwrap();
}
