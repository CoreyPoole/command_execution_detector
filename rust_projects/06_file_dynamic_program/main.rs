mod runner;
fn main(){ let input = std::fs::read_to_string("config").unwrap(); runner::execute(input); }
