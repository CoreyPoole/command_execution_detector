mod a;
mod b;
fn main(){ let input=std::env::args().nth(1).unwrap(); a::execute(input); }
