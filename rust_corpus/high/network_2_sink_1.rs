// CEDE corpus: high/network_2_sink_1 — network-derived data reaches a command (illustrative reqwest dependency)
use std::process::Command;
fn main() {
    let input=reqwest::blocking::get("https://example.test/api").unwrap().text().unwrap();
Command::new("sh").arg("-c").arg(input).spawn().unwrap();
}
