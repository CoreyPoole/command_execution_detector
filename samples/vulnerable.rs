use std::process::Command;
use std::io;

/// Docs mention Command::new("sh") but this is only a comment.
fn run_user_cmd() {
    let mut user = String::new();
    io::stdin().read_line(&mut user).unwrap();
    // Command::new("sh").arg("-c").arg(user);  <- commented out
    Command::new("sh").arg("-c").arg(user).spawn().unwrap();
}

fn run_env() {
    let v = std::env::var("TOOL").unwrap();
    Command::new(v).spawn().unwrap();
}

fn run_safe() {
    Command::new("git").arg("status").output().unwrap();
}

fn full_path_and_windows() {
    let t = std::process::Command::new("cmd").arg("/C").arg("dir").status();
    let line = "sh -c";
}
