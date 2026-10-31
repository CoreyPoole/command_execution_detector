
use std::process::Command;
use std::io;

fn safe_command() {
    Command::new("git").arg("status").output().unwrap();
}

// Case 1: User input reaches a shell
fn unsafe_shell() {
    let mut user = String::new();
    io::stdin().read_line(&mut user).unwrap();

    Command::new("sh")
        .arg("-c")
        .arg(user)
        .spawn()
        .unwrap();
}

// Case 2: External data selects the executable
fn unsafe_program() {
    let program = std::env::var("TOOL").unwrap();
    Command::new(program).spawn().unwrap();
}

// Case 3: Comment should not trigger detection
fn comments_only() {
    // Command::new("sh").arg("-c").arg(user).spawn();
}

// Case 4: Documentation string should not trigger
fn documentation_only() {
    let example = "sh -c echo hello";
    println!("{}", example);
}

// Case 5: Assignment happens after the command
fn assignment_order() {
    let mut input = String::from("hello");
    Command::new("echo").arg(&input).output().unwrap();

    input = std::env::var("UNTRUSTED").unwrap();
    println!("{}", input);
}
