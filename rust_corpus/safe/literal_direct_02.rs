// CEDE corpus: safe/literal_direct_02 — fixed executable and literal argument
use std::process::Command;
fn main() {
    Command::new("ls").arg("-la").status().unwrap();
}
