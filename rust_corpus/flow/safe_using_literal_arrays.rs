// CEDE corpus: flow/safe_using_literal_arrays — functions and command builder variants
use std::process::Command;
fn main(){Command::new("git").args(["status","--short"]).output().unwrap();}
