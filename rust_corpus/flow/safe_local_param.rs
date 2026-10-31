// CEDE corpus: flow/safe_local_param — functions and command builder variants
use std::process::Command;
fn run(value:String){Command::new("echo").arg(value).spawn().unwrap();}
fn main(){run(String::from("safe"));}
