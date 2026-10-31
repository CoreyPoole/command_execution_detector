// CEDE corpus: flow/identity_high — functions and command builder variants
use std::process::Command;
fn identity(s:String)->String{s}
fn main(){let value=std::env::args().nth(1).unwrap(); Command::new("sh").arg("-c").arg(identity(value)).spawn().unwrap();}
