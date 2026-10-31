use std::process::Command;

fn git_status() {
    Command::new("git").arg("status").output().unwrap();
}

fn list_dir() {
    let args: Vec<String> = std::env::args().collect();
    let dir = sanitize(&args[1]);
    Command::new("ls").arg(dir).output().unwrap();
}

fn sanitize(s: &str) -> String {
    s.chars().filter(|c| c.is_alphanumeric()).collect()
}
