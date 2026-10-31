// CEDE corpus: medium/env_4_sink_4 — environment value passed to a fixed executable
use std::process::Command;
fn main() {
    let value=std::env::var("PATH").unwrap(); Command::new("printf").arg(value).status().unwrap();
}
