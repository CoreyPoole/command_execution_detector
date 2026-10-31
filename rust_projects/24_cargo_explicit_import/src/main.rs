mod runner;
use crate::runner::execute;
fn main(){execute(std::env::var("ARG").unwrap());}
