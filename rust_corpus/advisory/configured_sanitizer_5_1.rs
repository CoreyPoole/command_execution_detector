// CEDE corpus: advisory/configured_sanitizer_5_1 — configured external sanitizer requires manual verification
use std::process::Command;
fn main() {
    let input = std::env::args().nth(1).unwrap();
 let safe = shell_escape::escape(&input);
 Command::new("echo").arg(safe).status().unwrap();
}
