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
# TODO: Add installation instructions
```

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
