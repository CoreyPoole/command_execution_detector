// CEDE corpus: safe/literal_direct_11 — fixed executable and literal argument
use std::process::Command;
fn main() {
    Command::new("printf").arg("hello").status().unwrap();
}
