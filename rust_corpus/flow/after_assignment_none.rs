// CEDE corpus: flow/after_assignment_none — ordering, branching, aliases and data flow
use std::process::Command;
fn main() {
    let mut value=String::from("safe"); Command::new("echo").arg(&value).status().unwrap(); value=std::env::var("LATER").unwrap();
}
