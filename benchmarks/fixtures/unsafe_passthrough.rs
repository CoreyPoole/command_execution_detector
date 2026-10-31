fn sanitize(s: String)->String { println!("Checked"); s }
fn main(){ let v=std::env::args().nth(1).unwrap(); std::process::Command::new("sh").arg("-c").arg(sanitize(v)).spawn().unwrap(); }
