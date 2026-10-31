fn main(){ let mut v=String::from("safe"); if true { v=std::env::args().nth(1).unwrap(); } std::process::Command::new("sh").arg("-c").arg(v).spawn().unwrap(); }
