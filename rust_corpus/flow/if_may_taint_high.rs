// CEDE corpus: flow/if_may_taint_high — ordering, branching, aliases and data flow
use std::process::Command;
fn main() {
    let mut command=String::from("safe"); if std::env::args().len()>1 {command=std::env::args().nth(1).unwrap();} Command::new("sh").arg("-c").arg(command).spawn().unwrap();
}
