// CEDE corpus: flow/static_shell_command_low — functions and command builder variants
use std::process::Command;
fn main(){Command::new("sh").arg("-c").arg("echo safe").spawn().unwrap();}
