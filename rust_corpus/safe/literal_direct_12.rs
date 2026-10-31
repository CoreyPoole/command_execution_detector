// CEDE corpus: safe/literal_direct_12 — fixed executable and literal argument
use std::process::Command;
fn main() {
    Command::new("id").arg("-u").status().unwrap();
}
