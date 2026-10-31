// CEDE corpus: advisory/local_alphanumeric_filter_plain — recognized local alphanumeric filter
use std::process::Command;
fn sanitize(s: &str) -> String { s.chars().filter(|c| c.is_alphanumeric()).collect() }
fn main() {
    let input=std::env::args().nth(1).unwrap(); Command::new("echo").arg(sanitize(&input)).status().unwrap();
}
