use pyo3_stub_gen::Result;

fn main() -> Result<()> {
    // Generate stubs for the entire _rust module
    println!("Getting stub info...");
    let stub = cflib_rust::stub_info()?;

    println!("Stub info: {:#?}", stub);

    println!("Generating stubs...");
    stub.generate()?;

    println!("Done!");
    Ok(())
}