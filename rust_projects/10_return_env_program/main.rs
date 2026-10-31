mod runner;
fn main(){ std::process::Command::new(runner::load()).spawn().unwrap(); }
