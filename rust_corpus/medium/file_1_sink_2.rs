// CEDE corpus: medium/file_1_sink_2 — file contents passed to a fixed executable
use std::process::Command;
fn main() {
    let value = std::fs::read_to_string("input.txt").unwrap(); Command::new("git").arg(value).output().unwrap();
}
