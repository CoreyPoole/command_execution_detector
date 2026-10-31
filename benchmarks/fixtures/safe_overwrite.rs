fn main(){ let mut v=std::env::var("CMD").unwrap(); v=String::from("status"); std::process::Command::new("git").arg(v).spawn().unwrap(); }
