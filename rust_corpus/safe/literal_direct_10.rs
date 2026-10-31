// CEDE corpus: safe/literal_direct_10 — fixed executable and literal argument
use std::process::Command;
fn main() {
    Command::new("true").arg("--help").status().unwrap();
}
