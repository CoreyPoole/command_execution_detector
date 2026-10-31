// CEDE corpus: medium/file_1_sink_1 — file contents passed to a fixed executable
use std::process::Command;
fn main() {
    let value = std::fs::read_to_string("input.txt").unwrap(); Command::new("echo").arg(value).status().unwrap();
}
