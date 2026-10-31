mod tools;
fn main(){ let input=std::env::args().nth(1).unwrap(); tools::runner::execute(input); }
