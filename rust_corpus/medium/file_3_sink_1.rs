// CEDE corpus: medium/file_3_sink_1 — file contents passed to a fixed executable
use std::process::Command;
fn main() {
    let value = std::fs::read_to_string("commands.txt").unwrap().trim().to_string(); Command::new("echo").arg(value).status().unwrap();
}
