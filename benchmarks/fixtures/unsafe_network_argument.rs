fn main(){ let v=reqwest::blocking::get("http://example.test").unwrap().text().unwrap(); std::process::Command::new("echo").arg(v).spawn().unwrap(); }
