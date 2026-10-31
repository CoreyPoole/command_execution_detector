use std::process::Command as Cmd; fn main(){let v=std::env::args().nth(1).unwrap(); Cmd::new("sh").args(["-c",&v]).spawn().unwrap(); }
