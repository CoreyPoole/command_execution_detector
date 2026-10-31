// CEDE corpus: flow/fake_sanitizer_high — functions and command builder variants
use std::process::Command;
fn sanitize(s:String)->String{println!("checked");s}
fn main(){let value=std::env::args().nth(1).unwrap(); Command::new("sh").arg("-c").arg(sanitize(value)).spawn().unwrap();}
