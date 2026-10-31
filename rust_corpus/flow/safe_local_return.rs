// CEDE corpus: flow/safe_local_return — functions and command builder variants
use std::process::Command;
fn get()->String{String::from("echo")}
fn main(){Command::new(get()).arg("safe").status().unwrap();}
