mod runner;
fn main(){let input=std::env::var("SECRET").unwrap(); println!("{}",input);runner::execute(String::from("hello"));}
