fn sanitize(s: &str)->String { s.chars().filter(|c| c.is_alphanumeric()).collect() }
fn main(){ let v=std::env::args().nth(1).unwrap(); std::process::Command::new("echo").arg(sanitize(&v)).spawn().unwrap(); }
