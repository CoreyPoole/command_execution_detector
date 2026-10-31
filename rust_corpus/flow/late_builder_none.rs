// CEDE corpus: flow/late_builder_none — ordering, branching, aliases and data flow
use std::process::Command;
fn main() {
    let mut cmd=Command::new("echo");cmd.arg("safe");cmd.spawn().unwrap();let input=std::env::args().nth(1).unwrap();cmd.arg(input);
}
