---
title: Reset EEPROM
page_id: eeprom 
---



The EEPROM stores configuration data, which persists even after a
firmware update. You might want to reset this information. For example,
if you forget the address of your Crazyflie, you won\'t be able to
connect wirelessly anymore. In order to reset the EEPROM, follow the
following steps:

1.  Unplug your Crazyradio
2.  Connect the Crazyflie to the PC using a USB-cable
3.  Execute the following from the examples

<!-- -->

    python3 write-eeprom.py

This will find your first Crazyflie (which is the one you connected over
USB) and write the default values to the EEPROM.
