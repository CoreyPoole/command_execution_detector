// CEDE corpus: flow/unsafe_local_return — functions and command builder variants
use std::process::Command;
fn get()->String{std::env::var("PROGRAM").unwrap()}
fn main(){Command::new(get()).status().unwrap();}
