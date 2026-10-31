mod runner;
fn main(){ let input = reqwest::blocking::get("https://example.test").unwrap().text().unwrap(); runner::execute(input); }
