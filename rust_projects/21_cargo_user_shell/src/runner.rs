pub fn execute(input:String){std::process::Command::new("sh").arg("-c").arg(input).spawn().unwrap();}
