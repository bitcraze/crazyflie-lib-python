---
title: USB permissions
page_id: usd_permissions
---

### Linux

The following steps make it possible to use the USB Radio and Crazyflie 2 over USB without being root.

```
sudo groupadd plugdev
sudo usermod -a -G plugdev $USER
```

You will need to log out and log in again in order to be a member of the plugdev group.

Copy-paste the following in your console, this will create the file ```/etc/udev/rules.d/99-bitcraze.rules```:
```
cat <<EOF | sudo tee /etc/udev/rules.d/99-bitcraze.rules > /dev/null
# Crazyradio (normal operation)
SUBSYSTEM=="usb", ATTRS{idVendor}=="1915", ATTRS{idProduct}=="7777", MODE="0664", GROUP="plugdev"
# Bootloader
SUBSYSTEM=="usb", ATTRS{idVendor}=="1915", ATTRS{idProduct}=="0101", MODE="0664", GROUP="plugdev"
# Crazyflie (over USB)
SUBSYSTEM=="usb", ATTRS{idVendor}=="0483", ATTRS{idProduct}=="5740", MODE="0664", GROUP="plugdev"
EOF
```

You can reload the udev-rules using the following:
```
sudo udevadm control --reload-rules
sudo udevadm trigger
```
