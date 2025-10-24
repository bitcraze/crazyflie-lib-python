# Crazyflie Python Library - Complete Feature Inventory

## Overview
This is an exhaustive inventory of ALL features, modules, subsystems, utilities, and infrastructure in the crazyflie-lib-python repository, version 0.1.29 (the stable version being rewritten).

The library is currently being rewritten in Rust (v1.0 Alpha), making this inventory critical for understanding what needs to be reimplemented.

---

## 1. CORE SUBSYSTEMS (cflib/crazyflie/)

### Main Crazyflie Connection Class
- **cflib/crazyflie/__init__.py** - Core Crazyflie class
  - Connection management (open_link, close_link, is_connected)
  - State management (DISCONNECTED, INITIALIZED, CONNECTED, SETUP_FINISHED)
  - Packet routing and callbacks
  - TOC (Table of Contents) caching (ro_cache, rw_cache)
  - Port callbacks for CRTP communication
  - Header callbacks with port/channel filtering
  - Packet sending with retry mechanism
  - Thread-safe incoming packet handler
  - Events/Callbacks:
    - `disconnected` - when link closes (intentional or not)
    - `connection_lost` - unintentional disconnect only
    - `link_established` - first packet received
    - `connection_requested` - user initiated connection
    - `connected` - link established, TOCs downloaded
    - `fully_connected` - all parameters downloaded
    - `connection_failed` - timeout
    - `disconnected_link_error` - error during disconnect state
    - `packet_received` - every packet
    - `packet_sent` - every packet sent
    - `link_quality_updated` - link quality changes

### 1.1 Commander (Low-Level Control)
- **cflib/crazyflie/commander.py**
  - Set motor control setpoints (roll, pitch, yaw rate, thrust)
  - Support for multiple setpoint types:
    - `TYPE_STOP` - stop all motors
    - `TYPE_VELOCITY_WORLD_LEGACY` - velocity in world frame
    - `TYPE_ZDISTANCE_LEGACY` - height control
    - `TYPE_HOVER_LEGACY` - hovering mode
    - `TYPE_FULL_STATE` - full state feedback control
    - `TYPE_POSITION` - position setpoint
    - `TYPE_VELOCITY_WORLD` - velocity control
    - `TYPE_ZDISTANCE` - altitude only
    - `TYPE_HOVER` - altitude hold
    - `TYPE_MANUAL` - manual control
  - X-mode (quadcopter orientation) support
  - Meta command notifications

### 1.2 High-Level Commander
- **cflib/crazyflie/high_level_commander.py**
  - Trajectory planning with 7th order polynomials
  - Commands:
    - `COMMAND_SET_GROUP_MASK` - group assignment
    - `COMMAND_STOP` - stop all motion
    - `COMMAND_GO_TO` - go to waypoint
    - `COMMAND_GO_TO_2` - enhanced go-to
    - `COMMAND_START_TRAJECTORY` - play trajectory
    - `COMMAND_START_TRAJECTORY_2` - enhanced trajectory
    - `COMMAND_DEFINE_TRAJECTORY` - define trajectory
    - `COMMAND_TAKEOFF_2` - takeoff with height/velocity
    - `COMMAND_LAND_2` - land with velocity
    - `COMMAND_SPIRAL` - spiral motion
  - Trajectory types:
    - `TRAJECTORY_TYPE_POLY4D` - 4D polynomial
    - `TRAJECTORY_TYPE_POLY4D_COMPRESSED` - compressed format
  - Trajectory storage in memory (location `TRAJECTORY_LOCATION_MEM`)
  - Group masking support (`ALL_GROUPS`)

### 1.3 Logging (Data Streaming)
- **cflib/crazyflie/log.py**
  - Dynamic log configuration creation
  - Table of Contents (TOC) for log variables
  - Log configuration management:
    - Create block on Crazyflie
    - Append variables to blocks
    - Delete blocks
    - Start/stop logging
  - Multiple channels: TOC, SETTINGS, LOGDATA
  - Command types:
    - `CMD_TOC_ELEMENT` - get TOC entry
    - `CMD_TOC_INFO` - get TOC info
    - `CMD_GET_ITEM_V2` - get log item (v2, up to 16k entries)
    - `CMD_GET_INFO_V2` - get info (v2)
    - `CMD_CREATE_BLOCK` - create log config
    - `CMD_APPEND_BLOCK` - add variable to config
    - `CMD_DELETE_BLOCK` - remove config
    - `CMD_START_LOGGING` - start data stream
  - Configuration states: Created on host → Created on CF → Started → Stopped → Deleted
  - Periodic data reporting
  - Fetch-as vs Stored-as type support

### 1.4 Parameters (Configuration)
- **cflib/crazyflie/param.py**
  - Get/set firmware parameters
  - Table of Contents for parameters
  - Persistent storage support:
    - `MISC_PERSISTENT_STORE` - save to persistent memory
    - `MISC_PERSISTENT_GET_STATE` - read persistent state
    - `MISC_PERSISTENT_CLEAR` - clear persistent storage
    - `MISC_GET_DEFAULT_VALUE` - read defaults
  - State management: IDLE, WAIT_TOC, WAIT_READ, WAIT_WRITE
  - Channels: TOC, READ, WRITE, MISC
  - Parameter name-based access
  - Type information (size, type)
  - Callbacks for all parameter updates
  - PersistentParamState tracking

### 1.5 Console
- **cflib/crazyflie/console.py**
  - Receive printf-style console messages from firmware
  - Simple callback interface: `receivedChar` callback
  - UTF-8 text decoding
  - CONSOLE port (0x00) communication

### 1.6 External Positioning (Extpos)
- **cflib/crazyflie/extpos.py**
  - Send external position to firmware:
    - `send_extpos(x, y, z)` - position only
    - `send_extpose(x, y, z, qx, qy, qz, qw)` - position + quaternion attitude
  - Forwards to position estimator
  - Uses Localization subsystem internally

### 1.7 Localization
- **cflib/crazyflie/localization.py**
  - Handles localization-related data communication
  - Generic location packet types:
    - `POSITION_CH` (0) - direct position
    - `GENERIC_CH` (1) - generic channel
  - Message types:
    - `RANGE_STREAM_REPORT` (0) - ranging data
    - `RANGE_STREAM_REPORT_FP16` (1) - FP16 ranging
    - `LPS_SHORT_LPP_PACKET` (2) - LPS UWB packet
    - `EMERGENCY_STOP` (3) - emergency stop signal
    - `EMERGENCY_STOP_WATCHDOG` (4) - watchdog timeout
    - `COMM_GNSS_NMEA` (6) - GNSS NMEA
    - `COMM_GNSS_PROPRIETARY` (7) - proprietary GNSS
    - `EXT_POSE` (8) - external pose
    - `EXT_POSE_PACKED` (9) - packed pose format
    - `LH_ANGLE_STREAM` (10) - lighthouse angle stream
    - `LH_PERSIST_DATA` (11) - lighthouse persistent data
  - Localization packet structure: type, raw_data, decoded_data
  - Callback: `receivedLocationPacket`
  - FP16 decoding support

### 1.8 Link Statistics
- **cflib/crazyflie/link_statistics.py**
  - Manages link quality metrics
  - Sub-components:
    - `Latency` - round-trip latency tracking
  - Statistics:
    - `latency_updated` - latency changes
    - `link_quality_updated` - overall quality
    - `uplink_rssi_updated` - receive signal strength
    - `uplink_rate_updated` - uplink rate
    - `downlink_rate_updated` - downlink rate
    - `uplink_congestion_updated` - uplink congestion
    - `downlink_congestion_updated` - downlink congestion
  - Ping/echo mechanism for latency
  - Start/stop control

### 1.9 App Channel
- **cflib/crazyflie/appchannel.py**
  - App-to-app communication channel
  - Send/receive arbitrary data packets
  - Uses PLATFORM port (0x0D), APP_CHANNEL (2)
  - Callback: `packet_received`

### 1.10 Platform Service
- **cflib/crazyflie/platformservice.py**
  - Fetch firmware version information
  - Get protocol version
  - Get firmware version
  - Platform control:
    - `PLATFORM_SET_CONT_WAVE` - continuous wave transmission
    - `PLATFORM_REQUEST_ARMING` - request arming
    - `PLATFORM_REQUEST_CRASH_RECOVERY` - recovery mode
  - Callbacks for version information

### 1.11 Synchronous Wrapper
- **cflib/crazyflie/syncCrazyflie.py**
  - Thread-safe synchronous wrapper around Crazyflie
  - Context manager support (with statement)
  - `is_connected()` - check connection
  - Wait for connection establishment
  - Connection timeout support
  - Access to underlying `.cf` (Crazyflie instance)

### 1.12 Synchronized Logger
- **cflib/crazyflie/syncLogger.py**
  - Synchronous logging interface
  - Iterator-based log data consumption
  - Context manager support
  - Automatic log block creation and cleanup
  - Timeout handling

### 1.13 Table of Contents (TOC)
- **cflib/crazyflie/toc.py**
  - TOC representation for parameters and logs
  - TOC element metadata
  - TOC fetching protocol
  - CRC validation
  - Version tracking

### 1.14 TOC Cache
- **cflib/crazyflie/toccache.py**
  - Filesystem-based TOC caching
  - Separate read-only and read-write caches
  - Cache validation
  - Firmware version-aware caching
  - CPU ID tracking

---

## 2. MEMORY SUBSYSTEM (cflib/crazyflie/mem/)

Core memory access and deck memory management.

### 2.1 Memory Base System
- **cflib/crazyflie/mem/__init__.py**
  - Core memory read/write operations
  - Memory request chunking (max 20 bytes per packet)
  - Multiple memory types support:
    - OW (One-Wire)
    - I2C
    - SPI
    - Flash
  - DMA support
  - Callback system for completion
  - Memory tester utility

### 2.2 Memory Element Classes
- **cflib/crazyflie/mem/memory_element.py**
  - Base class for memory elements
  - Address and size tracking
  - Read/write state machine
  - Type identification

### 2.3 I2C Element
- **cflib/crazyflie/mem/i2c_element.py**
  - I2C device memory access
  - Device address support
  - I2C-specific read/write

### 2.4 One-Wire Element
- **cflib/crazyflie/mem/ow_element.py**
  - One-Wire device support
  - One-Wire protocol handling

### 2.5 Deck Memory Manager
- **cflib/crazyflie/mem/deck_memory.py**
  - Manage memory for expansion decks
  - EEPROM read/write
  - Board identification via memory

### 2.6 Lighthouse Memory
- **cflib/crazyflie/mem/lighthouse_memory.py**
  - Lighthouse positioning system memory
  - Classes:
    - `LighthouseMemory` - main interface
    - `LighthouseMemHelper` - utilities
    - `LighthouseBsCalibration` - base station calibration
    - `LighthouseBsGeometry` - base station geometry
  - Read/write calibration data
  - Geometry configuration
  - Persistent storage

### 2.7 Lighthouse Memory (Alternate)
- **cflib/crazyflie/mem/led_driver_memory.py**
  - LED driver configuration
  - LED ring memory access

### 2.8 LED Timings Memory
- **cflib/crazyflie/mem/led_timings_driver_memory.py**
  - LED timing parameters
  - Timing configuration for LED rings

### 2.9 LocoMemory
- **cflib/crazyflie/mem/loco_memory.py**
  - Loco positioning system (UWB) memory
  - Anchor configuration
  - Initial support for memory management

### 2.10 LocoMemory2
- **cflib/crazyflie/mem/loco_memory_2.py**
  - Enhanced Loco positioning memory
  - Improved anchor management
  - Configuration v2

### 2.11 Multi-Ranger Memory
- **cflib/crazyflie/mem/multiranger_memory.py**
  - Multi-ranger deck memory
  - Sensor configuration
  - Calibration data

### 2.12 PAA3905 Memory
- **cflib/crazyflie/mem/paa3905_memory.py**
  - PAA3905 optical flow sensor memory
  - Sensor configuration
  - Calibration

### 2.13 Trajectory Memory
- **cflib/crazyflie/mem/trajectory_memory.py**
  - Trajectory storage in Crazyflie memory
  - Classes:
    - `Poly4D` - 4D polynomial trajectory
    - `CompressedStart` - compressed trajectory start point
    - `CompressedSegment` - compressed trajectory segment
    - `TrajectoryMemory` - trajectory manager
  - Upload/download trajectories
  - Compression support

### 2.14 Memory Tester
- **cflib/crazyflie/mem/memory_tester.py**
  - Memory integrity testing
  - Verify read/write operations

---

## 3. COMMUNICATION LAYER (cflib/crtp/)

CRTP (Crazyflie Real-Time Protocol) and communication drivers.

### 3.1 CRTP Stack
- **cflib/crtp/crtpstack.py**
  - CRTP packet definition
  - Packet structure with header, port, channel, data
  - Max payload: 30 bytes
  - Port definitions (CRTP protocol):
    - `CONSOLE` (0x00) - console output
    - `PARAM` (0x02) - parameters
    - `COMMANDER` (0x03) - commander setpoints
    - `MEM` (0x04) - memory access
    - `LOGGING` (0x05) - logging data
    - `LOCALIZATION` (0x06) - localization data
    - `COMMANDER_GENERIC` (0x07) - generic commander
    - `SETPOINT_HL` (0x08) - high-level setpoints
    - `PLATFORM` (0x0D) - platform services
    - `LINKCTRL` (0x0F) - link control
  - Channel support per port

### 3.2 CRTP Driver Base
- **cflib/crtp/crtpdriver.py**
  - Abstract base class for link drivers
  - Connect/disconnect interface
  - Send/receive packet handling
  - Statistics callback support

### 3.3 Radio Driver
- **cflib/crtp/radiodriver.py**
  - 2.4 GHz wireless communication
  - Crazyradio PA dongle support
  - URI format: `radio://<dongle>/<channel>/<datarate>/<address>`
  - Datarate options: 250K, 1M, 2M
  - Automatic retransmission (configurable)
  - Arc (automatic rate control)
  - Channel scanning
  - Shared radio instance pooling
  - Radio link statistics

### 3.4 Serial Driver
- **cflib/crtp/serialdriver.py**
  - UART/Serial communication
  - CPX (multi-core) support
  - Auto baud rate detection
  - URI format: `serial://<port>`
  - Port enumeration support
  - Cross-platform serial support
  - CPX packet routing

### 3.5 USB Driver
- **cflib/crtp/usbdriver.py**
  - Direct USB connection to Crazyflie
  - Bootloader mode detection
  - URI format: `usb://<device_index>`
  - Multiple device support
  - Statistics reporting

### 3.6 TCP Driver
- **cflib/crtp/tcpdriver.py**
  - TCP network communication
  - Remote Crazyflie connection
  - URI format: `tcp://<host>:<port>`
  - Timeout configuration

### 3.7 UDP Driver
- **cflib/crtp/udpdriver.py**
  - UDP network communication
  - Low-latency network transport
  - URI format: `udp://<host>:<port>`

### 3.8 CFLink C++ Driver
- **cflib/crtp/cflinkcppdriver.py**
  - C++ extension for CFLink protocol
  - High-performance communication

### 3.9 PRRT Driver
- **cflib/crtp/prrtdriver.py**
  - PRRT (Parallel Real-Time Ray Tracing) protocol
  - Specialized high-performance transport

### 3.10 Radio Link Statistics
- **cflib/crtp/radio_link_statistics.py**
  - Radio-specific link quality metrics
  - RSSI (Receive Signal Strength Indicator)
  - Packet loss tracking
  - Link rate monitoring

### 3.11 PCAP Support
- **cflib/crtp/pcap.py**
  - Packet capture for debugging
  - PCAP format export
  - Network packet logging

### 3.12 Exceptions
- **cflib/crtp/exceptions.py**
  - CRTP-specific exceptions
  - `WrongUriType` - URI format error
  - Connection errors

---

## 4. BOOTLOADER (cflib/bootloader/)

Firmware flashing and bootloader management.

### 4.1 Bootloader Core
- **cflib/bootloader/cloader.py**
  - Firmware upload to Crazyflie
  - Bootloader detection and mode switching
  - Classes:
    - `Cloader` - bootloader interface
  - Bootloader commands:
    - Scan for bootloader
    - Request boot mode
    - Flash firmware
    - Verify firmware
  - Target management
  - Flash page management
  - CPU ID retrieval
  - Protocol versioning
  - Automatic retry on boot URI

### 4.2 Bootloader Types
- **cflib/bootloader/boottypes.py**
  - Bootloader target definitions
  - Target types (STM32L, NRF, etc.)
  - Flash geometry
  - Memory mapping
  - Target identification

---

## 5. MULTI-CORE SUPPORT (cflib/cpx/)

Communication with multi-core Crazyflie platforms.

### 5.1 CPX Router
- **cflib/cpx/__init__.py**
  - CPX (Crazyflie Packet eXchange) protocol
  - Packet routing between cores
  - Enums:
    - `CPXTarget` - target processor (STM32, ESP32, HOST, GAP8)
    - `CPXFunction` - function types (SYSTEM, CONSOLE, CRTP, WIFI_CTRL, APP, TEST, BOOTLOADER)
  - `CPXPacket` class - packet structure with routing
  - Version tracking
  - Destination/source routing
  - Last packet flag

### 5.2 CPX Transports
- **cflib/cpx/transports.py**
  - UART transport for CPX
  - SerialTransport class
  - Serial configuration
  - Packet serialization/deserialization

---

## 6. POSITIONING & MOTION (cflib/positioning/)

High-level motion control and positioning helpers.

### 6.1 Motion Commander
- **cflib/positioning/motion_commander.py**
  - Velocity-based motion primitives
  - Classes:
    - `MotionCommander` - motion control
  - Methods:
    - `take_off()` - takeoff and hover
    - `land()` - land safely
    - Distance-based primitives (forward, backward, left, right, up, down)
    - Non-blocking motion starts
    - Motion blocking/waiting
    - Hovering at default height
    - Velocity-based control
    - Rotation commands
    - Default velocity and rotation rate configuration
  - Thread-based motion controller
  - Context manager support (automatic takeoff/land)
  - Heading/yaw management

### 6.2 Position High-Level Commander
- **cflib/positioning/position_hl_commander.py**
  - Position-based waypoint navigation
  - Classes:
    - `PositionHLCommander` - position control
  - Methods:
    - `go_to()` - go to waypoint
    - Trajectory planning
    - Multi-point sequences
  - Context manager support
  - Position tracking

---

## 7. LOCALIZATION SUBSYSTEM (cflib/localization/)

Advanced localization algorithms, especially Lighthouse positioning.

### 7.1 Lighthouse Geometry Solver
- **cflib/localization/lighthouse_geometry_solver.py**
  - Solve base station positions from sweep data
  - Non-linear optimization
  - Bundle adjustment
  - Multi-base station support
  - Crazyflie pose estimation
  - Sensor configuration
  - Error estimation and validation
  - Iterative solving

### 7.2 Lighthouse Initial Estimator
- **cflib/localization/lighthouse_initial_estimator.py**
  - Initial position estimation from lighthouse
  - Starting point for optimization
  - Geometric calculations

### 7.3 Lighthouse System Aligner
- **cflib/localization/lighthouse_system_aligner.py**
  - Align lighthouse system to world coordinates
  - Coordinate transformation
  - System registration
  - Rotation/translation matrices

### 7.4 Lighthouse System Scaler
- **cflib/localization/lighthouse_system_scaler.py**
  - Scale lighthouse coordinate system
  - Metric scale determination
  - Reference distance calibration

### 7.5 Lighthouse Sample Matcher
- **cflib/localization/lighthouse_sample_matcher.py**
  - Match lighthouse sweep samples
  - Data association
  - Correspondence finding
  - Outlier rejection

### 7.6 Lighthouse Sweep Angle Reader
- **cflib/localization/lighthouse_sweep_angle_reader.py**
  - Parse lighthouse sweep angle data
  - Raw sensor data processing
  - Angle extraction from sensor readings

### 7.7 Lighthouse Base Station Vector
- **cflib/localization/lighthouse_bs_vector.py**
  - Base station geometry representation
  - Pose and orientation
  - Vector mathematics

### 7.8 Lighthouse Types
- **cflib/localization/lighthouse_types.py**
  - Type definitions for lighthouse system
  - Data structures
  - Enums for system states

### 7.9 Lighthouse Config Manager
- **cflib/localization/lighthouse_config_manager.py**
  - Manage lighthouse system configuration
  - Base station configuration
  - Persistent storage
  - Load/save configurations

### 7.10 IPPE (Iterative Perspective-n-Point with EPnP)
- **cflib/localization/ippe_cf.py**
  - Pose estimation algorithm for Crazyflie
  - Perspective-n-point solving
  - Camera-less position estimation
  - Crazyflie-specific implementation

### 7.11 IPPE Core
- **cflib/localization/_ippe.py**
  - EPnP (Efficient Perspective-n-Point) algorithm
  - Core mathematical implementation
  - Pose recovery

### 7.12 Parameter I/O
- **cflib/localization/param_io.py**
  - Parameter file management for localization
  - Read/write configuration files
  - YAML format support
  - ParamFileManager class

---

## 8. UTILITIES (cflib/utils/)

Helper classes and utility functions.

### 8.1 Callbacks Framework
- **cflib/utils/callbacks.py**
  - `Caller` class - event/callback system
  - `add_callback()` - register handler
  - `call()` - trigger callbacks
  - Synchronous/asynchronous support

### 8.2 Encoding Utilities
- **cflib/utils/encoding.py**
  - `fp16_to_float()` - half-precision float conversion
  - `compress_quaternion()` - quaternion compression
  - Data type conversions
  - Network byte order handling

### 8.3 Multi-Ranger Utilities
- **cflib/utils/multiranger.py**
  - Multi-ranger deck helper
  - Distance measurements
  - 360-degree obstacle detection

### 8.4 Parameter File Helper
- **cflib/utils/param_file_helper.py**
  - Synchronous parameter file operations
  - Load parameters from file to Crazyflie
  - Persistent storage integration
  - Wait for completion

### 8.5 Power Switch Utility
- **cflib/utils/power_switch.py**
  - Control auxiliary power switches
  - Enable/disable power to accessories

### 8.6 Reset Estimator
- **cflib/utils/reset_estimator.py**
  - Reset position estimator
  - Initialize Kalman filter
  - Trajectory reset

### 8.7 URI Helper
- **cflib/utils/uri_helper.py**
  - Parse CRTP URIs
  - URI validation
  - Extract components (driver, address, etc.)
  - Generate URIs programmatically

---

## 9. HARDWARE DRIVERS (cflib/drivers/)

Low-level hardware access.

### 9.1 Crazyradio Driver
- **cflib/drivers/crazyradio.py**
  - Crazyradio PA USB dongle interface
  - PyUSB-based communication
  - Device enumeration
  - Firmware version detection
  - Channel/datarate configuration
  - Packet transmission/reception
  - Automatic retransmission
  - ACK handling
  - Device initialization
  - Power amplifier control

### 9.2 CFUSB Driver
- **cflib/drivers/cfusb.py**
  - Crazyflie USB bootloader interface
  - Firmware flashing protocol
  - Bulk transfers
  - Device open/close
  - Bootloader mode access

---

## 10. SWARM CONTROL (cflib/crazyflie/swarm.py)

Multi-Crazyflie coordination.

- **Swarm class** - coordinate multiple Crazyflies
  - Context manager support
  - `open_links()` / `close_links()`
  - `parallel_safe()` - parallel action execution
  - `sequential_safe()` - sequential action execution
  - Factory pattern for Crazyflie creation
  - Cached TOC factory option
  - Position tracking
  - Synchronized actions
  - Leader-follower patterns
  - Swarm-wide state management

- **CachedCfFactory** - create Crazyflies with cached TOCs

---

## 11. EXAMPLES (examples/)

Comprehensive example scripts organized by functionality:

### 11.1 Autonomy Examples
- `autonomy/autonomous_sequence.py` - autonomous flight
- `autonomy/autonomous_sequence_high_level.py` - HL commander sequences
- `autonomy/autonomous_sequence_high_level_compressed.py` - compressed trajectories
- `autonomy/circling_square_demo.py` - circular and square paths
- `autonomy/full_state_setpoint_demo.py` - full state control
- `autonomy/motion_commander_demo.py` - motion commander usage
- `autonomy/position_commander_demo.py` - position setpoints

### 11.2 Motion Control
- `motors/ramp.py` - motor thrust ramp
- `motors/multiramp.py` - multi-motor ramp
- `positioning/flowsequence_sync.py` - optical flow sequences
- `positioning/initial_position.py` - set initial position
- `positioning/matrix_light_printer.py` - LED display control

### 11.3 Logging and Data
- `logging/basiclog.py` - basic logging example
- `logging/basiclog_sync.py` - synchronous logging
- `link_quality/latency.py` - measure link latency
- `radio/radio_test.py` - radio performance testing
- `radio/scan.py` - frequency scan

### 11.4 Parameters
- `parameters/basicparam.py` - get/set parameters
- `parameters/persistent_params.py` - persistent storage
- `parameters/persistent_params_from_file.py` - load params from file

### 11.5 Memory Operations
- `memory/read_eeprom.py` - read EEPROM
- `memory/write_eeprom.py` - write EEPROM
- `memory/read_ow.py` - read one-wire memory
- `memory/write_ow.py` - write one-wire memory
- `memory/erase_ow.py` - erase one-wire
- `memory/read_l5.py` - read L5 memory
- `memory/flash_memory.py` - flash memory operations
- `memory/read_deck_mem.py` - read expansion deck memory
- `memory/read_paa3905.py` - read optical flow sensor config

### 11.6 Positioning Systems
- `lighthouse/lighthouse_openvr_grab.py` - Lighthouse with OpenVR
- `lighthouse/lighthouse_openvr_grab_color.py` - with color support
- `lighthouse/lighthouse_openvr_multigrab.py` - multi-deck support
- `lighthouse/multi_bs_geometry_estimation.py` - base station geometry
- `lighthouse/read_lighthouse_mem.py` - read lighthouse calibration
- `lighthouse/write_lighthouse_mem.py` - write lighthouse calibration
- `loco_nodes/lps_reboot_to_bootloader.py` - anchor bootloader

### 11.7 Sensor Integration
- `multiranger/multiranger_pointcloud.py` - 3D obstacle map
- `multiranger/multiranger_push.py` - obstacle sensing
- `multiranger/multiranger_wall_following.py` - wall follower
- `multiranger/wall_following/wall_following.py` - wall following algorithm

### 11.8 Motion Capture Integration
- `mocap/mocap_hl_commander.py` - mocap with HL commander
- `mocap/qualisys_hl_commander.py` - Qualisys integration

### 11.9 LED Control
- `led-ring/led_param_set.py` - LED parameters
- `led-ring/led_mem_set.py` - LED memory control
- `led-ring/led_timing.py` - LED timing control

### 11.10 AI Deck
- `aideck/fpv.py` - AI deck first-person video

### 11.11 Console
- `console/console.py` - console output capture

### 11.12 Swarm Examples
- `swarm/swarm_sequence.py` - coordinated sequences
- `swarm/swarm_sequence_circle.py` - circular formation
- `swarm/synchronized_sequence.py` - synchronized actions
- `swarm/hl_commander_swarm.py` - swarm with HL commander
- `swarm/leader_follower.py` - leader-follower control
- `swarm/asynchronized_swarm.py` - async swarm control

### 11.13 Bridge/Network
- `cfbridge.py` - network bridge to Crazyflie

### 11.14 Step-by-Step Tutorials
- `step-by-step/sbs_connect_log_param.py` - connection, logging, params
- `step-by-step/sbs_motion_commander.py` - motion control tutorial
- `step-by-step/sbs_swarm.py` - swarm tutorial

---

## 12. TESTING (test/)

Unit tests and test infrastructure.

### 12.1 Crazyflie Tests
- `test/crazyflie/test_syncCrazyflie.py` - sync wrapper tests
- `test/crazyflie/test_syncLogger.py` - sync logger tests
- `test/crazyflie/test_swarm.py` - swarm functionality tests
- `test/crazyflie/test_localization.py` - localization tests
- `test/crazyflie/mem/test_lighthouse_memory.py` - lighthouse memory tests

### 12.2 CRTP Tests
- `test/crtp/test_crtpstack.py` - packet handling tests

### 12.3 Positioning Tests
- `test/positioning/test_motion_commander.py` - motion commander tests
- `test/positioning/test_position_hl_commander.py` - position commander tests

### 12.4 Localization Tests
- `test/localization/test_lighthouse_geometry_solver.py`
- `test/localization/test_lighthouse_initial_estimator.py`
- `test/localization/test_lighthouse_system_aligner.py`
- `test/localization/test_lighthouse_system_scaler.py`
- `test/localization/test_lighthouse_sample_matcher.py`
- `test/localization/test_lighthouse_bs_vector.py`
- `test/localization/test_lighthouse_config_manager.py`
- `test/localization/test_lighthouse_types.py`
- `test/localization/test_ippe_cf.py`
- `test/localization/test_param_io.py`
- `test/localization/lighthouse_fixtures.py` - test fixtures
- `test/localization/lighthouse_test_base.py` - base test class

### 12.5 Test Support
- `test/support/asyncCallbackCaller.py` - async test helper

### 12.6 Test Fixtures
- `test/localization/fixtures/parameters.yaml` - test parameters
- `test/localization/fixtures/system_config.yaml` - system config
- `test/utils/fixtures/five_params.yaml` - parameter files
- `test/utils/fixtures/single_param.yaml`

---

## 13. DOCUMENTATION (docs/)

### 13.1 API Documentation
- `docs/api/index.md` - API index
- `docs/api/cflib/index.md` - cflib API docs

### 13.2 User Guides
- `docs/user-guides/index.md` - guides index
- `docs/user-guides/python_api.md` - Python API reference
- `docs/user-guides/sbs_connect_log_param.py` - tutorial
- `docs/user-guides/sbs_motion_commander.md` - motion tutorial
- `docs/user-guides/sbs_swarm_interface.md` - swarm tutorial

### 13.3 Development Docs
- `docs/development/index.md` - dev guide
- `docs/development/eeprom.md` - EEPROM info
- `docs/development/uart_communication.md` - UART details
- `docs/development/matlab.md` - MATLAB integration
- `docs/development/wireshark.md` - packet capture

### 13.4 Functional Areas
- `docs/functional-areas/index.md` - features index
- `docs/functional-areas/crazyradio_lib.md` - Crazyradio documentation

### 13.5 Installation
- `docs/installation/index.md` - installation guide
- `docs/installation/install.md` - detailed installation
- `docs/installation/usb_permissions.md` - USB setup

---

## 14. BUILD & INFRASTRUCTURE

### 14.1 Project Configuration
- `pyproject.toml` - project metadata and dependencies
  - Build backend: setuptools
  - Python >= 3.10 required
  - Dependencies: pyusb, libusb-package, scipy, numpy, packaging
  - Optional: qualisys, motioncapture modules
  - Package discovery with exclude patterns
  - Resource package data configuration

### 14.2 CI/CD Pipeline
- `.github/workflows/CI.yml` - main CI workflow
  - Docker-based build (bitcraze/builder)
  - Documentation build
  - Runs on: push to master, PR, weekly schedule
- `.github/workflows/nightly.yml` - nightly builds
- `.github/workflows/python-publish.yml` - PyPI publishing
- `.github/workflows/test-python-publish.yml` - test PyPI

### 14.3 Code Quality
- `.pre-commit-config.yaml` - pre-commit hooks
  - Code formatting
  - Linting checks
  - Type checking

### 14.4 Build Tools
- `tools/build/build` - main build script
- `tools/build-docs/build-docs` - documentation builder
- `tools/crtp-dissector.lua` - Wireshark dissector for CRTP

### 14.5 System Tests
- `sys_test/single_cf_grounded/README.md` - single Crazyflie tests
- `sys_test/swarm_test_rig/README.md` - swarm testing setup

### 14.6 Resources
- `cflib/resources/binaries/` - firmware binaries directory

---

## 15. ADDITIONAL INFRASTRUCTURE

### 15.1 License
- `LICENSE.txt` - GPLv3 license

### 15.2 README
- `README.md` - project overview

### 15.3 Caching
- `examples/cache/.gitkeep` - log cache directory

---

## SUMMARY STATISTICS

| Category | Count | Notes |
|----------|-------|-------|
| Core subsystems | 14 | Crazyflie, Commander, Log, Param, etc. |
| Memory element types | 10 | Lighthouse, Loco, Multi-ranger, LED, etc. |
| CRTP Drivers | 10 | Radio, Serial, USB, TCP, UDP, etc. |
| Localization modules | 12 | Lighthouse geometry, IPPE, alignment, etc. |
| Utilities | 7 | Callbacks, encoding, parameters, etc. |
| Example categories | 14 | Autonomy, motors, logging, positioning, etc. |
| Example scripts | 50+ | Comprehensive coverage of all features |
| Test modules | 10+ | Unit tests for major components |
| Documentation sections | 5 | API, user guides, development, functional areas |

---

## KEY ARCHITECTURAL CONCEPTS

1. **Port-based routing**: CRTP uses ports (CONSOLE, PARAM, COMMANDER, etc.) with channels for multiplexing
2. **Table of Contents (TOC)**: Dynamic discovery of logs and parameters with caching
3. **Callback system**: Event-driven architecture with Caller class
4. **Synchronous wrappers**: SyncCrazyflie and SyncLogger for blocking operations
5. **Memory chunking**: Large reads/writes split into 20-byte packets
6. **Factory pattern**: Swarm factory for flexible Crazyflie creation
7. **Context managers**: Automatic setup/teardown (connection, takeoff/land)
8. **Thread-safe design**: Incoming packet handler thread, locks for send operations
9. **Module-based drivers**: Pluggable transport drivers (radio, serial, USB, TCP, UDP)
10. **Lighthouse positioning**: Complete computational geometry implementation for positioning

---

## DEPENDENCIES

**Core**:
- pyusb ~1.2 - USB hardware access
- libusb-package ~1.0 - USB driver
- scipy ~1.14 - Scientific computing
- numpy ~2.2 - Numerical computing
- packaging ~25.0 - Version handling

**Optional**:
- qtm-rt ~3.0.2 - Qualisys motion capture
- motioncapture ~1.0a4 - Generic mocap interface

**Development**:
- pre-commit - code quality checks

---

## SUPPORTED PLATFORMS

- Linux
- macOS
- Windows

---

## SUPPORTED PYTHON VERSIONS

- Python 3.10
- Python 3.11
- Python 3.12
- Python 3.13

