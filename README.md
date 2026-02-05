# Crazyflie Python Library

**Rust-powered Python library for Crazyflie quadcopters**

> **v1.0 Alpha** - Complete rewrite with breaking changes. Use [v0.1.29](https://github.com/bitcraze/crazyflie-lib-python/tree/v0.1.29) for the stable version.

---

## Quick Start

```python
# TODO: Add minimal example
```

---

## Installation

```bash
# TODO: Add installation instructions for end users
```

---

## Development Setup

### Prerequisites
- Rust toolchain (cargo)
- Python 3.10+
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
cargo run --bin stub_gen --manifest-path rust/Cargo.toml --no-default-features
```

The `--no-default-features` flag is required because the default `extension-module` feature tells PyO3 not to link against libpython (extension modules get those symbols from the Python interpreter). The stub generator is a standalone binary, so it needs libpython linked directly.

Pre-commit hooks will automatically run linting and formatting on commit.

---

## Implementation Status

> **Note:** Documentation and unit testing are ongoing activities alongside each feature, not separate checkboxes.

### Core Connection & Protocol
- [ ] Connection management (open/close, state machine, callbacks)
- [ ] CRTP protocol layer (packet structure, ports, channels)
- [ ] TOC (Table of Contents) caching system
- [ ] Link statistics (latency, RSSI, packet loss)
- [ ] URI parsing and validation

### Transport Drivers
- [ ] Radio driver (Crazyradio PA, 2.4 GHz)
- [ ] Serial driver (UART/CPX)
- [ ] USB driver (direct USB connection)
- [ ] TCP driver (network)
- [ ] UDP driver (network)

### Core Subsystems
- [ ] Commander (low-level control: roll, pitch, yaw, thrust)
- [ ] High-level commander (trajectories, takeoff, land, go-to)
- [ ] Logging (dynamic log configuration, data streaming)
- [ ] Parameters (get/set, persistent storage)
- [ ] Console (printf output from firmware)
- [ ] Platform service (firmware version, device info)
- [ ] App channel (arbitrary data packets)

### Memory Subsystem
- [ ] Memory core (read/write with chunking)
- [ ] Lighthouse memory (calibration, geometry)
- [ ] Trajectory memory (Poly4D trajectories)
- [ ] Loco memory (UWB anchors)
- [ ] LED driver memory
- [ ] Deck memory (expansion boards)
- [ ] Multi-ranger memory

### Positioning & Localization
- [ ] External positioning (send position/pose to CF)
- [ ] Localization messages (range, UWB, GNSS, ext pose)
- [ ] Lighthouse localization (sweep angles, geometry solver)
- [ ] IPPE (pose estimation algorithm)

### High-Level APIs
- [ ] Motion commander (velocity control, distance-based movement)
- [ ] Position high-level commander (waypoint navigation)
- [ ] Synchronous wrappers (SyncCrazyflie, SyncLogger)

### Multi-Crazyflie Support
- [ ] Swarm interface (parallel/sequential actions)
- [ ] CPX router (multi-core support for AI deck)

### Utilities
- [ ] Callback/event system
- [ ] FP16 ↔ float conversion
- [ ] Quaternion compression
- [ ] Parameter file I/O (YAML)
- [ ] Reset estimator helper

### Bootloader
- [ ] Firmware flashing
- [ ] Target management
- [ ] Protocol versioning

### Infrastructure
- [ ] Examples (basic, motors, logging, positioning, swarm, etc.)
- [ ] CI/CD (GitHub Actions)
- [ ] Build system (maturin, Rust compilation)
- [ ] Platform support (Linux, macOS, Windows)
- [ ] Python compatibility (3.10, 3.11, 3.12, 3.13)

---

## What Changed in v1.0.0?

*TODO: Add migration guide*

---

## Documentation

*TODO: Add docs link*

---

## Contributing

*TODO: Add contributing guidelines*

---

## License

GPLv3 - see [LICENSE](LICENSE)
