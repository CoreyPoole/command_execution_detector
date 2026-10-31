mod runner;
use crate::runner::execute;
fn main(){ let input=std::env::args().nth(1).unwrap(); execute(input); }
