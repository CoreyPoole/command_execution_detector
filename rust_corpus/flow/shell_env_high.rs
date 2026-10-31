// CEDE corpus: flow/shell_env_high — ordering, branching, aliases and data flow
use std::process::Command;
fn main() {
    let input=std::env::var("INJECT").unwrap(); Command::new("sh").arg("-c").arg(input).spawn().unwrap();
}
