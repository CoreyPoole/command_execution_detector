pub fn execute(input: String){ std::process::Command::new(input).status().unwrap(); }
