pub fn execute(){std::process::Command::new("sh").arg("-c").arg("echo safe").status().unwrap();}
