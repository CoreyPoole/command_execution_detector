// CEDE corpus: high/network_1_sink_3 — network-derived data reaches a command (illustrative reqwest dependency)
use std::process::Command;
fn main() {
    let input=reqwest::blocking::get("https://example.test").unwrap().text().unwrap();
Command::new(input).status().unwrap();
}
