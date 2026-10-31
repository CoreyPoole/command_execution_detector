// CEDE corpus: advisory/configured_sanitizer_3_2 — configured external sanitizer requires manual verification
use std::process::Command;
fn main() {
    let input = std::env::args().nth(1).unwrap();
 let safe = escape(&input);
 Command::new("sh").arg("-c").arg(safe).status().unwrap();
}
