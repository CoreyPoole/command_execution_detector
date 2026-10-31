// CEDE corpus: flow/unsafe_local_param — functions and command builder variants
use std::process::Command;
fn run(value:String){Command::new("sh").arg("-c").arg(value).spawn().unwrap();}
fn main(){run(std::env::args().nth(1).unwrap());}
