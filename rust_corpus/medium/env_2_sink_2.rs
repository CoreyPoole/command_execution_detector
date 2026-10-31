// CEDE corpus: medium/env_2_sink_2 — environment value passed to a fixed executable
use std::process::Command;
fn main() {
    let value=std::env::var("FLAG").expect("required"); Command::new("git").arg(value).output().unwrap();
}
