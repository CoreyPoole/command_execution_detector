// CEDE corpus: flow/alias_command_high — functions and command builder variants
use std::process::Command;
use std::process::Command as Cmd;
fn main(){ let input=std::env::args().nth(1).unwrap(); Cmd::new("sh").arg("-c").arg(input).spawn().unwrap(); }
