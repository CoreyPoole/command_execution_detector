// CEDE corpus: advisory/configured_sanitizer_3_1 — configured external sanitizer requires manual verification
use std::process::Command;
fn main() {
    let input = std::env::args().nth(1).unwrap();
 let safe = escape(&input);
 Command::new("echo").arg(safe).status().unwrap();
}
