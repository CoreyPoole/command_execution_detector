pub fn execute(input:String){std::process::Command::new("echo").arg(input).status().unwrap();}
