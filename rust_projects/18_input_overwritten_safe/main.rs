mod runner;
fn main(){ let mut input=std::env::args().nth(1).unwrap(); input=String::from("safe"); runner::execute(input); }
