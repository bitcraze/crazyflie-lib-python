# Crazyflie Python Library - Architecture Summary

## High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                     User Applications                           │
│         (Examples, scripts, user code)                          │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────────┐
│                    High-Level APIs                              │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   Motion     │  │   Swarm      │  │  Positioning │          │
│  │  Commander  │  │  Control     │  │   Helpers    │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  HL Command  │  │  Localization│  │   Console    │          │
│  │  (Trajectory)│  │   (Location)  │  │   (Printf)   │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────────┐
│              Core Crazyflie Subsystems                           │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  Commander   │  │  Logging     │  │  Parameters  │          │
│  │(Low-Level)   │  │  (Data)      │  │  (Config)    │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  Memory      │  │  External    │  │   Platform   │          │
│  │  Subsystem   │  │  Positioning │  │   Service    │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │  Extpos      │  │  AppChannel  │  │  LinkStats   │          │
│  │(Ext Pose)    │  │  (App Data)  │  │  (Quality)   │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────────┐
│            Crazyflie Core Class (Connection)                    │
│  - Connection/disconnection logic                               │
│  - Packet routing via ports and channels                        │
│  - TOC caching                                                   │
│  - Thread-safe packet handling                                  │
│  - Callback registration and management                         │
│  - State management (DISCONNECTED → SETUP_FINISHED)             │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────────┐
│            CRTP Layer (Packet Protocol)                         │
│  - Packet definition (header, port, channel, data)              │
│  - Port definitions (CONSOLE, PARAM, COMMANDER, etc.)           │
│  - Max payload: 30 bytes                                        │
│  - Port-based routing                                           │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────────┐
│           Transport Drivers (Pluggable)                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   Radio      │  │   Serial     │  │    USB       │          │
│  │  (Crazyradio)│  │  (CPX/UART)  │  │  (Bootload)  │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐          │
│  │   TCP        │  │    UDP       │  │  CFLink C++  │          │
│  │  (Network)   │  │  (Network)   │  │  (Extension) │          │
│  └──────────────┘  └──────────────┘  └──────────────┘          │
└─────────────────────────────────────────────────────────────────┘
                              │
┌─────────────────────────────────────────────────────────────────┐
│           Hardware & Link Interface                             │
│  - Crazyradio PA USB dongle (2.4 GHz)                           │
│  - Direct USB connection to Crazyflie                           │
│  - Serial/UART (with CPX multi-core routing)                   │
│  - Network (TCP/UDP)                                            │
│  - Link statistics (RSSI, latency, packet loss)                │
└─────────────────────────────────────────────────────────────────┘
                              │
                      ┌───────┴───────┐
                      │               │
                  Crazyflie      Bootloader
                  (Firmware)      (Upload)
```

## Module Dependencies

```
User Code
  ├── High-Level APIs
  │   ├── positioning/motion_commander.py
  │   ├── positioning/position_hl_commander.py
  │   ├── localization/* (Lighthouse)
  │   └── utils/* (Helpers)
  │
  └── Crazyflie class (cflib/crazyflie/__init__.py)
      ├── commander.py (COMMANDER port 0x03)
      ├── high_level_commander.py (SETPOINT_HL port 0x08)
      ├── log.py (LOGGING port 0x05)
      ├── param.py (PARAM port 0x02)
      ├── console.py (CONSOLE port 0x00)
      ├── localization.py (LOCALIZATION port 0x06)
      ├── extpos.py (via localization)
      ├── mem/__init__.py (MEM port 0x04)
      │   ├── lighthouse_memory.py
      │   ├── loco_memory.py
      │   ├── trajectory_memory.py
      │   ├── led_driver_memory.py
      │   ├── multiranger_memory.py
      │   └── ... (10 memory types)
      ├── appchannel.py (PLATFORM port 0x0D, ch 2)
      ├── platformservice.py (PLATFORM port 0x0D)
      ├── link_statistics.py (link quality)
      ├── toc.py (Table of Contents)
      ├── toccache.py (TOC caching)
      ├── syncCrazyflie.py (Thread-safe wrapper)
      ├── syncLogger.py (Sync logging)
      └── swarm.py (Multi-Crazyflie)
          ├── SyncCrazyflie (uses sync wrapper)
          └── CachedCfFactory (with TOC cache)

      Crazyflie communicates via:
      └── Link (CRTPDriver subclass)
          ├── radiodriver.py
          │   └── drivers/crazyradio.py (USB hardware)
          ├── serialdriver.py
          │   ├── pyserial
          │   └── cpx/ (multi-core routing)
          ├── usbdriver.py
          │   └── drivers/cfusb.py (USB hardware)
          ├── tcpdriver.py
          ├── udpdriver.py
          ├── cflinkcppdriver.py (C++ extension)
          └── prrtdriver.py

Utilities:
├── callbacks.py (Caller pattern)
├── encoding.py (fp16, quaternion)
├── multiranger.py (obstacle detection)
├── param_file_helper.py (parameter files)
├── power_switch.py (accessory power)
├── reset_estimator.py (Kalman init)
└── uri_helper.py (URI parsing)

Bootloader:
└── bootloader/cloader.py (Firmware flashing)
    └── bootloader/boottypes.py (Target definitions)

CPX (Multi-core):
├── cpx/__init__.py (CPX routing)
└── cpx/transports.py (UART transport)
```

## CRTP Port Mapping

The CRTP protocol uses ports to route messages:

```
Port 0x00: CONSOLE      - Printf output from firmware
Port 0x02: PARAM        - Parameter get/set
Port 0x03: COMMANDER    - Motor setpoints (low-level)
Port 0x04: MEM          - Memory read/write (EEPROM, deck memory, etc.)
Port 0x05: LOGGING      - Data streaming (periodic measurements)
Port 0x06: LOCALIZATION - Position/pose data (external, lighthouse, UWB)
Port 0x07: COMMANDER_GENERIC - Alternative commander (less common)
Port 0x08: SETPOINT_HL  - High-level setpoints (trajectory, go-to)
Port 0x0D: PLATFORM     - Platform info, firmware version, arming
Port 0x0F: LINKCTRL     - Link control and statistics
```

Each port has multiple channels for different functions.

## Connection State Machine

```
DISCONNECTED
    │
    ├─ open_link() called
    ↓
INITIALIZED
    │
    ├─ First packet received
    ↓
CONNECTED
    │
    ├─ TOC download
    ├─ Parameter fetch
    ├─ Memory info
    ├─ Platform info
    ↓
SETUP_FINISHED
    │
    ├─ All initial handshake complete
    └─ Ready for normal operation
    
    At any state:
    └─ close_link() → DISCONNECTED
```

## Memory Type Hierarchy

```
MemoryElement (base class)
├── I2CElement
│   └── Specific I2C devices
├── OWElement
│   └── One-Wire devices
├── DeckMemoryManager
│   └── Expansion deck EEPROM
├── LighthouseMemory
│   ├── LighthouseMemHelper
│   ├── LighthouseBsCalibration
│   └── LighthouseBsGeometry
├── LocoMemory (UWB)
├── LocoMemory2 (UWB v2)
├── LEDDriverMemory
├── LEDTimingsDriverMemory
├── MultirangerMemory
├── PAA3905Memory (optical flow)
└── TrajectoryMemory
    ├── Poly4D
    ├── CompressedStart
    └── CompressedSegment
```

## Localization System Architecture

The Lighthouse positioning system has a complete implementation:

```
Raw sweep angle data
    ↓
LighthouseSweepAngleReader (parse angles)
    ↓
LighthouseSampleMatcher (associate measurements)
    ↓
LighthouseInitialEstimator (starting point)
    ↓
LighthouseGeometrySolver (optimize base station positions)
    │   ├─ Bundle adjustment
    │   ├─ Non-linear optimization
    │   └─ Multi-base station support
    ↓
LighthouseSystemAligner (align to world frame)
    ↓
LighthouseSystemScaler (determine metric scale)
    ↓
LighthouseConfigManager (persistent storage)
    ↓
Position estimate + calibration data

Alternative:
IPPE algorithm (ippe_cf.py) for pose estimation
└─ EPnP (Efficient Perspective-n-Point) mathematical core
```

## Callback System Architecture

All asynchronous events use the `Caller` pattern:

```
Caller class:
  - add_callback(function) - register handler
  - call(*args, **kwargs) - trigger all callbacks

Used for:
- crazyflie.disconnected.add_callback(on_disconnect)
- crazyflie.connected.add_callback(on_connect)
- crazyflie.connection_failed.add_callback(on_fail)
- crazyflie.packet_received.add_callback(on_packet)
- crazyflie.packet_sent.add_callback(on_sent)
- crazyflie.log.data_received.add_callback(on_log_data)
- crazyflie.param.all_updated.add_callback(on_params_ready)
- ... and many more subsystem-specific callbacks
```

## Summary of Major Components

| Component | Lines | Purpose |
|-----------|-------|---------|
| Crazyflie class | 479 | Core connection and routing |
| Log | ~400 | Data streaming and logging |
| Param | ~350 | Parameter management |
| Commander | ~200 | Low-level motor control |
| HighLevelCommander | ~300 | Trajectory planning |
| Memory | ~300 | Memory I/O |
| RadioDriver | ~500 | Wireless communication |
| Lighthouse Geometry Solver | ~400 | Positioning computation |
| Various utilities | ~1000 | Helpers and special cases |
| **Total Python LOC** | **~8000+** | Comprehensive framework |

