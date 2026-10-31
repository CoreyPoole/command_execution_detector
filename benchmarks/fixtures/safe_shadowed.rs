fn main(){ let v=String::from("safe"); { let v=std::env::args().nth(1).unwrap(); println!("{}",v); } std::process::Command::new("echo").arg(v).spawn().unwrap(); }
