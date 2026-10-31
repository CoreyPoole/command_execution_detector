mod runner;
fn main(){ let input = std::env::args().nth(1).unwrap(); runner::execute(input); }
