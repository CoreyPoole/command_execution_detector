// CEDE corpus: high/user_2_sink_5 — untrusted user input to process execution
use std::process::Command;
fn main() {
    let input = std::env::args().last().unwrap();
 Command::new("git").arg(input).spawn().unwrap();
}
