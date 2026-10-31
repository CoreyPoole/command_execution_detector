// CEDE corpus: flow/if_overwrite_none — ordering, branching, aliases and data flow
use std::process::Command;
fn main() {
    let mut command=String::from("safe"); if true { command=std::env::var("X").unwrap(); } command=String::from("safe again"); Command::new("echo").arg(command).spawn().unwrap();
}
