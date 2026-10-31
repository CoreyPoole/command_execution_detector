pub fn execute(){std::process::Command::new("cmd").arg("/C").arg("echo hi").status().unwrap();}
