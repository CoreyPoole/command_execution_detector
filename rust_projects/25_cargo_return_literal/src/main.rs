mod runner;
fn main(){std::process::Command::new("echo").arg(runner::load()).spawn().unwrap();}
