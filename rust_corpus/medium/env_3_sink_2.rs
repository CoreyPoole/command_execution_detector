// CEDE corpus: medium/env_3_sink_2 — environment value passed to a fixed executable
use std::process::Command;
fn main() {
    let value=std::env::var("HOME").unwrap().to_string(); Command::new("git").arg(value).output().unwrap();
}
