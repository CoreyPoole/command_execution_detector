// CEDE corpus: high/user_1_sink_1 — untrusted user input to process execution
use std::process::Command;
fn main() {
    let input = std::env::args().nth(1).unwrap();
 Command::new("sh").arg("-c").arg(input).spawn().unwrap();
}
