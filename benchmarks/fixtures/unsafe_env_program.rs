fn main(){ let program=std::env::var("CMD").unwrap(); std::process::Command::new(program).spawn().unwrap(); }
