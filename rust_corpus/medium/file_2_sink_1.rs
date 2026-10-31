// CEDE corpus: medium/file_2_sink_1 — file contents passed to a fixed executable
use std::process::Command;
fn main() {
    let value = std::fs::read_to_string("settings.toml").expect("read"); Command::new("echo").arg(value).status().unwrap();
}
