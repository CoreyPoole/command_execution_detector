// CEDE corpus: safe/literal_direct_04 — fixed executable and literal argument
use std::process::Command;
fn main() {
    Command::new("pwd").arg(".").status().unwrap();
}
