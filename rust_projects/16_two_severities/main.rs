mod runner;
fn main(){ let u=std::env::args().nth(1).unwrap(); let e=std::env::var("X").unwrap(); runner::high(u); runner::medium(e); }
