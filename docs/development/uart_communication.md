---
title: UART communication
page_id: uart_communication
---

This page describes how to control your Crazyflie via UART, e.g. with a direct connection to a Raspberry Pi or with your computer through an FTDI cable.

## Physical Connection

To control the Crazyflie via UART first establish a physical connection between the Crazyflie and the controlling device. On the Crazyflie use the pins for UART2 which are on the right expansion connector TX2 (pin 1) and RX2 (pin 2).

If you are connecting to a Raspberry Pi look for the UART pins there connect them as follows

- Crazyflie TX2 -- Raspberry Pi RX
- Crazyflie RX2 -- Raspberry Pi TX
- Crazyflie Gdn -- Raspberry Pi Gdn (if not both connected to same powersource)

## Crazyflie Firmware

Typically the Crazyflie expects control commands from Radio or Bluetooth and also sends its feedback there. To change this to UART, the crazyflie-firmware has to be compiled with the following [kbuild configurations](https://www.bitcraze.io/documentation/repository/crazyflie-firmware/master/development/kbuild/) with `make menuconfig`
* `Expansion deck configuration`-> `Force load specified custom deck driver`->fill in `cpxOverUART2`
* `Expansion deck configuration`->`Support wired external host using CPX on UART`-> include in build with `y`

## Controlling Device

On the controlling device the Python library `crazyflie-lib-python` can be used to send commands to the Crazyflie via UART if some additional dependencies are installed and UART is properly set up to be used.

### UART setup Raspberry Pi

A prerequisite for controlling the Crazyflie via UART is that UART is properly set up. The following steps are tested with a Raspberry Pi Zero and a Raspberry Pi 3B+. Depending on what Raspberry Pi version you use some steps might be skipped or be a bit different. Additional information can be found in the [Raspberry Pi UART documentation](https://www.raspberrypi.org/documentation/configuration/uart.md).

- Enable the mini UART (`/dev/ttyS0`) in `/boot/config.txt`: `enable_uart=1`

- Restore `/dev/ttyAMA0` as primary UART in `/boot/config.txt`: `dtoverlay=miniuart-bt`

  This step is not necessary, but might be desirable as the mini UART is less capable than the PL011 UART. If you skip this step use the mini UART (`/dev/ttyS0`) to communicate with the Crazyflie.

  (You can confirm that ttyAMA0 is the primary UART by using `ls -l /dev/` and looking for `serial0 -> ttyAMA0`.)

- Disable login shell with `sudo raspi-config`: Interfacing Options->Serial->disable Login Shell/enable serial hardware port

- Allow the user to use the UART device: `sudo usermod -a -G dialout $USER`

  (You can confirm that the user is listed in the dialout group with `groups` and that the device belongs to the group with `ls -l /dev/ttyAMA0` or `ls -l /dev/ttyS0`.)

### Additional Dependencies

The Python library needs `pyserial` as an additional dependency for the UART communication. To install `pyserial` use `pip3 install pyserial`. (You can confirm that pyserial indeed finds your UART port by `python3 -m serial.tools.list_ports -v`.)

## Usage

Once everything is set up you should be able to control the Crazyflie via UART.

Add the parameter `enable_serial_driver=True` to `cflib.crtp.init_drivers()` and connect to the Crazyflie using a serial URI.
The serial URI has the form `serial://<name>` (e.g. `serial://ttyAMA0`, `serial://ttyUSB5`) or if the OS of the controlling device does not provide the name `serial://<device>` (e.g. `serial:///dev/ttyAMA0`).

The following script might give an idea on how a first test of the setup might look like to print the log variables of the Crazyflie on the Raspberry pi

```python
#!/usr/bin/env python3

import logging
import time

import cflib.crtp
from cflib.crazyflie import Crazyflie
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from cflib.crazyflie.log import LogConfig
from cflib.crazyflie.syncLogger import SyncLogger

# choose the serial URI that matches the setup serial device
URI = 'serial://ttyAMA0'

def console_callback(text: str):
    print(text, end='')
    
if __name__ == '__main__':
    # Initialize the low-level drivers including the serial driver
    cflib.crtp.init_drivers(enable_serial_driver=True)
    cf = Crazyflie(rw_cache='./cache')
    cf.console.receivedChar.add_callback(console_callback)
    
    lg_stab = LogConfig(name='Stabilizer', period_in_ms=10)
    lg_stab.add_variable('stabilizer.roll', 'float')
    lg_stab.add_variable('stabilizer.pitch', 'float')
    lg_stab.add_variable('stabilizer.yaw', 'float')


    with SyncCrazyflie(URI) as scf:
        print('[host] Connected, use ctrl-c to quit.')
        with SyncLogger(scf, lg_stab) as logger:
            endTime = time.time() + 10
            for log_entry in logger:
                timestamp = log_entry[0]
                data = log_entry[1]
                logconf_name = log_entry[2]

                print('[%d][%s]: %s' % (timestamp, logconf_name, data))

                if time.time() > endTime:
                    break

```

## Troubleshooting

* If you see the a `CRC error` when running the script, make sure to install the cflib from source. 
* If the script hangs with connecting, restart the crazyflie
