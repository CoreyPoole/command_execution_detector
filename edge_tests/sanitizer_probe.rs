use std::process::Command;

fn validate(s: String) -> String {
    s
}

fn main() {
    let input = std::env::args().nth(1).unwrap();
    let cleaned = validate(input);
    Command::new("sh").arg("-c").arg(cleaned).spawn().unwrap();
}