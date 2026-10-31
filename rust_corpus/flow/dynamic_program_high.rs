// CEDE corpus: flow/dynamic_program_high — ordering, branching, aliases and data flow
use std::process::Command;
fn main() {
    let input=std::fs::read_to_string("program").unwrap(); Command::new(input).status().unwrap();
}
