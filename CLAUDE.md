# Context for Claude Code

## Project Goal

This repository is undergoing a **complete rewrite from v0.1.29 to v1.0**, transitioning from a pure Python implementation to **Rust-powered Python bindings**.

### Key Changes
- **Architecture**: Pure Python → Rust core with Python bindings (via PyO3)
- **API Style**: Callback-based → Context manager & async-aware
- **Connection Model**: Stateful Crazyflie object → Connection-based lifecycle
- **Version**: v0.1.29 (stable) → v1.0.0-alpha (breaking rewrite)

### Repository Scope
This Python repository:
- ✅ Exposes Rust functionality via PyO3 bindings
- ✅ Provides Python convenience wrappers where helpful
- ✅ Maintains examples and documentation
- ✅ Tracks what Python API features exist

This repository does NOT:
- ❌ Decide what features go into the Rust library (that's [crazyflie-lib-rs](https://github.com/ataffanel/crazyflie-lib-rs))
- ❌ Implement CRTP protocol, transport drivers, or core logic (Rust does that)

### Current Status
- Working on `rik/rust` branch
- Basic features (Commander, Params, Console, Platform) have initial Rust bindings
- Most features not yet implemented
- See [README.md](README.md) for detailed implementation status

## Reference Documentation

### Old Library Reference (v0.1.29)
These documents describe the OLD Python library being replaced. Use them to understand what features existed and how they worked:

- **[COMPLETE_FEATURE_INVENTORY.md](COMPLETE_FEATURE_INVENTORY.md)** (985 lines)
  - Exhaustive list of all 60+ modules, subsystems, and features in v0.1.29
  - Organized by category: Core subsystems, memory types, drivers, positioning, utilities, examples, etc.
  - Use this to understand "what features did the old lib have?"

- **[ARCHITECTURE_SUMMARY.md](ARCHITECTURE_SUMMARY.md)** (289 lines)
  - Visual architecture overview of v0.1.29
  - Layer diagrams, dependency graphs, CRTP protocol structure
  - Connection state machine, memory hierarchy, callback patterns
  - Use this to understand "how did the old lib work?"

### Current Work
- **[README.md](README.md)** - Current status, feature checklist, quick start
- **[rust/](rust/)** - PyO3 bindings to crazyflie-lib-rs
- **[examples/rust_example.py](examples/rust_example.py)** - Example of new API style

## Branch Strategy
- `master` - Contains v0.1.29 (stable, callback-based Python lib)
- `rik/rust` - Active development branch for v1.0 rewrite
- Eventually: Merge to main as v1.0.0-alpha, iterate with alpha/beta releases

## Development Notes
- Using `maturin` for Rust/Python integration
- Python 3.10+ required (abi3 compatibility)
- The old lib had ~12K lines of Python across 77 files
- Starting from scratch (most files deleted) to avoid fighting the new architecture
