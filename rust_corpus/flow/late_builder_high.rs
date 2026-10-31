// CEDE corpus: flow/late_builder_high — ordering, branching, aliases and data flow
use std::process::Command;
fn main() {
    let mut cmd=Command::new("sh"); let input=std::env::args().nth(1).unwrap(); cmd.arg("-c");cmd.arg(input);cmd.spawn().unwrap();
}
