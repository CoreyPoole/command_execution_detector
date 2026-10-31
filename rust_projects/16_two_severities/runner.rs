pub fn high(input:String){std::process::Command::new("sh").arg("-c").arg(input).spawn().unwrap();}
pub fn medium(input:String){std::process::Command::new("echo").arg(input).spawn().unwrap();}
