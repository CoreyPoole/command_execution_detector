fn main(){ std::process::Command::new("sh").arg("-c").arg("echo hi").spawn().unwrap(); }
