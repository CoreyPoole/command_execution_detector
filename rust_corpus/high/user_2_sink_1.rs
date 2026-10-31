// CEDE corpus: high/user_2_sink_1 — untrusted user input to process execution
use std::process::Command;
fn main() {
    let input = std::env::args().last().unwrap();
 Command::new("sh").arg("-c").arg(input).spawn().unwrap();
}
