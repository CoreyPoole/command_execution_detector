// CEDE corpus: safe/literal_direct_07 — fixed executable and literal argument
use std::process::Command;
fn main() {
    Command::new("uname").arg("-a").status().unwrap();
}
