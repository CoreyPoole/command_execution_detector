fn main(){ std::process::Command::new("git").arg("status").output().unwrap(); }
