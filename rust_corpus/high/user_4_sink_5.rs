// CEDE corpus: high/user_4_sink_5 — untrusted user input to process execution
use std::process::Command;
fn main() {
    let mut input = String::new(); std::io::stdin().read_line(&mut input).unwrap();
 Command::new("git").arg(input).spawn().unwrap();
}
