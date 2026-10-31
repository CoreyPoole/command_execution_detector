// CEDE corpus: safe/literal_direct_06 — fixed executable and literal argument
use std::process::Command;
fn main() {
    Command::new("date").arg("+%F").status().unwrap();
}
