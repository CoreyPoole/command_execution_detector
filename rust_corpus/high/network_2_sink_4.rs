// CEDE corpus: high/network_2_sink_4 — network-derived data reaches a command (illustrative reqwest dependency)
use std::process::Command;
fn main() {
    let input=reqwest::blocking::get("https://example.test/api").unwrap().text().unwrap();
Command::new("echo").arg(input).output().unwrap();
}
