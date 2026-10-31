pub fn high(a:String){std::process::Command::new("sh").arg("-c").arg(a).spawn().unwrap();}
pub fn medium(b:String){std::process::Command::new("echo").arg(b).spawn().unwrap();}
