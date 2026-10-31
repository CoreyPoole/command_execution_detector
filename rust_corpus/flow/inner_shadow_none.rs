// CEDE corpus: flow/inner_shadow_none — ordering, branching, aliases and data flow
use std::process::Command;
fn main() {
    let input=String::from("safe"); {let input=std::env::args().nth(1).unwrap();println!("{}",input);} Command::new("echo").arg(input).spawn().unwrap();
}
