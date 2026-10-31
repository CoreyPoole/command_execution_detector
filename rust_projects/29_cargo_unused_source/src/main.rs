mod runner;
fn main(){let bad=std::env::args().nth(1).unwrap(); println!("{}",bad); runner::execute(String::from("safe"));}
