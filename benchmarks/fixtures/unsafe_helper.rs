fn run(v:String){ std::process::Command::new("echo").arg(v).spawn().unwrap(); }
fn main(){run(std::env::args().nth(1).unwrap());}
