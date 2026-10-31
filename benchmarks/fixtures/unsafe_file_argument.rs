fn main(){ let v=std::fs::read_to_string("input").unwrap(); std::process::Command::new("echo").arg(v).spawn().unwrap(); }
