// CEDE corpus: flow/unsafe_shell_arg_array — functions and command builder variants
use std::process::Command;
fn main(){let x=std::env::args().nth(1).unwrap();Command::new("sh").args(["-c",&x]).status().unwrap();}
