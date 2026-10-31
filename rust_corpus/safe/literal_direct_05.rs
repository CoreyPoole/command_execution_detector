// CEDE corpus: safe/literal_direct_05 — fixed executable and literal argument
use std::process::Command;
fn main() {
    Command::new("whoami").arg("--help").status().unwrap();
}
