mod runner;
fn main(){ let input = std::env::var("CMD").unwrap(); runner::execute(input); }
