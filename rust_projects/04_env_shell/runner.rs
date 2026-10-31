pub fn execute(input: String){ std::process::Command::new("bash").arg("-c").arg(input).spawn().unwrap(); }
