mod runner;
fn main(){std::process::Command::new(runner::load()).status().unwrap();}
