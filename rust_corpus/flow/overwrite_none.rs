// CEDE corpus: flow/overwrite_none — ordering, branching, aliases and data flow
use std::process::Command;
fn main() {
    let mut value=std::env::args().nth(1).unwrap(); value=String::from("safe"); Command::new("echo").arg(value).status().unwrap();
}
