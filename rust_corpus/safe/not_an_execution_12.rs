// CEDE corpus: safe/not_an_execution_12 — comments and harmless shell-like strings
use std::process::Command;
fn main() {
    let m = ("sh", "-c", "echo"); println!("{:?}", m);
}
