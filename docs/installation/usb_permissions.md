---
title: USB permissions
page_id: usd_permissions
---

### Linux

The following steps make it possible to use the USB Radio without being root.

```
sudo groupadd plugdev
sudo usermod -a -G plugdev $USER
```

You will need to log out and log in again in order to be a member of the plugdev group.

Create a file named ```/etc/udev/rules.d/99-crazyradio.rules``` and add the
following:
```
# Crazyradio (normal operation)
SUBSYSTEM=="usb", ATTRS{idVendor}=="1915", ATTRS{idProduct}=="7777", MODE="0664", GROUP="plugdev"
# Bootloader
SUBSYSTEM=="usb", ATTRS{idVendor}=="1915", ATTRS{idProduct}=="0101", MODE="0664", GROUP="plugdev"
```

To connect Crazyflie 2.0 via usb, create a file name ```/etc/udev/rules.d/99-crazyflie.rules``` and add the following:
```
SUBSYSTEM=="usb", ATTRS{idVendor}=="0483", ATTRS{idProduct}=="5740", MODE="0664", GROUP="plugdev"
```

You can reload the udev-rules using the following:
```
sudo udevadm control --reload-rules
sudo udevadm trigger
```
