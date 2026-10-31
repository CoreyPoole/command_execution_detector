// CEDE corpus: flow/before_env_medium — ordering, branching, aliases and data flow
use std::process::Command;
fn main() {
    let mut value=String::from("safe"); value=std::env::var("X").unwrap(); Command::new("echo").arg(value).status().unwrap();
}
