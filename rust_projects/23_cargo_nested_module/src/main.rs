mod tools;
fn main(){let x=std::env::args().nth(1).unwrap(); tools::runner::execute(x);}
