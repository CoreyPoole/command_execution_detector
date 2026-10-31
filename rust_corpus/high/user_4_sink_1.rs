// CEDE corpus: high/user_4_sink_1 — untrusted user input to process execution
use std::process::Command;
fn main() {
    let mut input = String::new(); std::io::stdin().read_line(&mut input).unwrap();
 Command::new("sh").arg("-c").arg(input).spawn().unwrap();
}
