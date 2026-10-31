// CEDE corpus: flow/format_positional_high — ordering, branching, aliases and data flow
use std::process::Command;
fn main() {
    let input=std::env::args().nth(1).unwrap(); let command=format!("echo {}",input); Command::new("sh").arg("-c").arg(command).spawn().unwrap();
}
