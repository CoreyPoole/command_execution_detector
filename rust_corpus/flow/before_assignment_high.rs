// CEDE corpus: flow/before_assignment_high — ordering, branching, aliases and data flow
use std::process::Command;
fn main() {
    let mut value=String::from("safe"); value=std::env::args().nth(1).unwrap(); Command::new("sh").arg("-c").arg(value).status().unwrap();
}
