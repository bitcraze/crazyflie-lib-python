# Crazyflie Python Library

**Rust-powered Python library for Crazyflie quadcopters**

> This library is a ground-up rewrite with breaking changes from the original [cflib](https://github.com/bitcraze/crazyflie-lib-python). The API is async-first, powered by Rust via PyO3, and is not yet stable. Expect breaking changes.

---

## Quick Start

```python
import asyncio
from cflib import Crazyflie, LinkContext

async def main():
    context = LinkContext()

    # Scan for Crazyflies
    uris = await context.scan(address=list(bytes.fromhex("E7E7E7E7E7")))
    print(f"Found: {uris}")

    # Connect and read a parameter
    cf = await Crazyflie.connect_from_uri(context, "radio://0/80/2M/E7E7E7E7E7")
    param = cf.param()
    value = await param.get("pm.lowVoltage")
    print(f"Low voltage threshold: {value}V")
    await cf.disconnect()

asyncio.run(main())
```

See the [examples/](examples/) directory for more.

---

## Development Setup

### Prerequisites
- Rust toolchain (cargo)
- [uv](https://docs.astral.sh/uv/) package manager

### Initial Setup

1. **Install dependencies:**
   ```bash
   uv sync --group dev
   ```

2. **Install pre-commit hooks:**
   ```bash
   uv run pre-commit install
   ```

3. **Build the project:**
   ```bash
   cargo build --lib --manifest-path rust/Cargo.toml && \
   uv run maturin develop && \
   uv sync && \
   uvx ruff check . && \
   uvx ruff format .
   ```

### Development Workflow

After making changes to Rust code, rebuild with:
```bash
cargo build --lib --manifest-path rust/Cargo.toml && \
uv run maturin develop && \
uv sync && \
uvx ruff check . && \
uvx ruff format .
```

This uses **debug mode** for faster compilation during development.

### Performance Testing During Development

To benchmark or test performance locally with optimizations enabled:
```bash
cargo build --release --lib --manifest-path rust/Cargo.toml && \
uv run maturin develop --release
```

> **Note:** When users `pip install` your package (from git or PyPI), maturin automatically builds in release mode. This section is only for testing optimized performance during local development.

### Regenerating Python Stubs

To regenerate `cflib/_rust.pyi` after changing the Rust API:
```bash
cargo run --bin stub_gen --manifest-path rust/Cargo.toml --no-default-features && \
uv run scripts/fix_stubs.py cflib/_rust.pyi
```

The `--no-default-features` flag is required because the default `extension-module` feature tells PyO3 not to link against libpython (extension modules get those symbols from the Python interpreter). The stub generator is a standalone binary, so it needs libpython linked directly.

The `fix_stubs.py` script converts `Coroutine[Any, Any, T]` return types to `async def ... -> T`, which is needed because our async methods use `pyo3-async-runtimes` (not native `async fn`) and `pyo3_stub_gen` can't detect them as async.

Pre-commit hooks will automatically run linting and formatting on commit.

---

## License

GPLv3 - see [LICENSE](LICENSE)
