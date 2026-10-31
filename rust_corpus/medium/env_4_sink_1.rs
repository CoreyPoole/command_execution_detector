// CEDE corpus: medium/env_4_sink_1 — environment value passed to a fixed executable
use std::process::Command;
fn main() {
    let value=std::env::var("PATH").unwrap(); Command::new("echo").arg(value).status().unwrap();
}
