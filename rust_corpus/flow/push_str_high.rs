// CEDE corpus: flow/push_str_high — ordering, branching, aliases and data flow
use std::process::Command;
fn main() {
    let mut input=String::new(); std::io::stdin().read_line(&mut input).unwrap(); let mut line=String::from("echo "); line.push_str(&input); Command::new("sh").arg("-c").arg(line).spawn().unwrap();
}
