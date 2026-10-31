// CEDE corpus: flow/after_env_none — ordering, branching, aliases and data flow
use std::process::Command;
fn main() {
    let mut value=String::from("safe"); Command::new("git").arg(value.clone()).status().unwrap(); value=std::env::var("LATER").unwrap();
}
