// CEDE corpus: safe/literal_direct_03 — fixed executable and literal argument
use std::process::Command;
fn main() {
    Command::new("echo").arg("hello").status().unwrap();
}
