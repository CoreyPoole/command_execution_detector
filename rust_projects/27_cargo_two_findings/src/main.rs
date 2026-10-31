mod runner;
fn main(){ let a=std::env::args().nth(1).unwrap(); let b=std::env::var("VAL").unwrap(); runner::high(a); runner::medium(b);}
