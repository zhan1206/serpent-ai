fn main() {
    // Build script for PyO3
    println!("cargo:rerun-if-changed=src/lib.rs");
}
