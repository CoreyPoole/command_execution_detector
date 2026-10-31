// CEDE corpus: medium/env_3_sink_4 — environment value passed to a fixed executable
use std::process::Command;
fn main() {
    let value=std::env::var("HOME").unwrap().to_string(); Command::new("printf").arg(value).status().unwrap();
}
