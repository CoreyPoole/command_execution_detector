fn main(){ let mut x = String::new(); std::io::stdin().read_line(&mut x).unwrap(); std::process::Command::new("sh").arg("-c").arg(x).spawn().unwrap(); }
