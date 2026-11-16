---
title: Experimental Bluetooth Low Energy transport
page_id: ble
---

The optional BLE driver provides bench inspection and telemetry without a
Crazyradio. It has been hardware-tested on macOS 15.7.4 / Apple Silicon and a
Crazyflie 2.1. Other operating systems, multiple simultaneous devices, flight,
and radio-equivalent timing/range have not been validated.

## Install and discover

Install this branch with its optional backend:

```sh
python -m pip install '.[ble]'
```

Enable the driver explicitly. To discover only BLE, use its scanner directly:

```python
import cflib.crtp
from cflib.crtp.bledriver import BleDriver

cflib.crtp.init_drivers(enable_ble_driver=True)
for uri, _description in BleDriver().scan_interface():
    print(uri)
```

The existing Radio, USB and network drivers remain available. A scan through
`cflib.crtp.scan_interfaces()` scans all registered drivers, including radio;
radio traffic can disable BLE in the Crazyflie until it is restarted. Close
other clients before connecting. macOS Bluetooth permission is required;
CoreBluetooth scanning here is active, not strictly passive.

URIs have the form `ble://<CoreBluetooth UUID>?name=<exact advertised name>`.
The UUID is local to macOS, not a portable MAC address. Discovery uses the
advertised name because the tested firmware does not advertise the proprietary
CRTP service UUID. Connection validates the selected UUID/name and GATT profile.
This avoids selecting the first device by name; it is not authentication.

## Read-only bench session

Use the discovered URI with ordinary `Crazyflie`, `SyncCrazyflie`, `LogConfig`
and parameter-read APIs. The connection initializes the log/parameter TOCs and
reads parameter values; uncached startup can take several minutes. On the tested
unit there were 525 logging items and 310 parameters. Three real sessions
completed, including 40 voltage samples and confirmed cleanup of owned blocks.
These observations are not performance guarantees for other hardware.

The transport always blocks flight/setpoint ports, supervisor commands,
parameter writes, raw-memory accesses and bootloader payloads. It permits
identification, TOC/parameter reads, memory metadata and bounded TOC-based log
configuration. It avoids a global log reset and cleans up only blocks whose
creation succeeded in this session. Up to four owned blocks are allowed, with a
minimum logging period of 100 ms. There is no URI option to enable flight.

The normal cflib close-time setpoint is also blocked before transmission. Packet
statistics count blocked requests separately from transmitted data.

## Firmware compatibility and failure handling

The [companion nRF CRTPUP fix](https://github.com/bitcraze/crazyflie2-nrf-firmware/pull/127) is required. Legacy nRF 2024.10 was observed losing
byte 19 of long DOWN packets. The driver never guesses a missing byte. It drains
startup messages, then checks exact echo data at 8, 20 and 31 bytes before cflib
initialization. Incompatible framing/data causes a failed connection.

BLE IO runs in a dedicated event-loop thread, with bounded queues and operation
timeouts. UP/DOWN use the documented length-minus-one/PID framing. BLE request
retries have an 800 ms minimum to avoid premature retries with ATT writes and
null polling; other drivers retain their existing timeout. A health echo and
10-second receive watchdog detect a stalled connection. Disconnects, queue
errors and framing errors stop the session and notify cflib.

This driver does not install firmware. Updating the application and bootloader
are separate operations. Tests use a fake backend and do not require Bleak or a
Bluetooth adapter:

```sh
python -m unittest discover -s test -p test_ble_driver.py
```


## Review dependencies

The [standalone framing prerequisite](https://github.com/bitcraze/crazyflie-lib-python/pull/613)
contains only the wire codec and its tests. This driver branch carries the same
codec files until that prerequisite is incorporated upstream. The mandatory
bench packet policy is separate in `cflib.crtp.blepolicy`; the wire codec has no
policy or Bleak dependency.
