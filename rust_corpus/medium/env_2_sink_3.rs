// CEDE corpus: medium/env_2_sink_3 — environment value passed to a fixed executable
use std::process::Command;
fn main() {
    let value=std::env::var("FLAG").expect("required"); Command::new("ls").arg(value).spawn().unwrap();
}
