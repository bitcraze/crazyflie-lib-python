# cflib: Crazyflie python library [![Build Status](https://api.travis-ci.org/bitcraze/crazyflie-lib-python.svg)](https://travis-ci.org/bitcraze/crazyflie-lib-python)

cflib is an API written in Python that is used to communicate with the Crazyflie
and Crazyflie 2.0 quadcopters. It is intended to be used by client software to
communicate with and control a Crazyflie quadcopter. For instance the [cfclient][cfclient] Crazyflie PC client uses the cflib.

For more info see our [wiki](http://wiki.bitcraze.se/ "Bitcraze Wiki").

Installation
------------

See [bellow](#platform-notes) for platform specific instruction.

In this section you should replace ```python``` by the version you are using
(usually either ```python2``` or ```python3```). Installing for [cfclient][cfclient] requires python3

The only dependency is pyusb:
```
python -m pip install "pyusb>=1.0.0b2"
```

To install cflib as a system-wide library (as root):
```
python setup.py install
```

To install cflib as a system-wide library (as user):
```
python -m pip install --user -e .
```

To install cflib in development mode where you can then edit the code on place:
```
python -m pip install -e .
```

To uninstall any of the above:
```
python -m pip uninstall cflib
```

Examples
--------

Examples on how to use cflib to communicate with Crazyflie can be found in the
example folder. To run the example you should install cflib following
the [installation](#installation) section.

Platform notes
--------------

## Linux

### Setup script

To install the Crazyflie PC client in Linux, you can run the setup script with:

```sudo setup_linux.sh```

This will install the Crazyflie lib syste-mwide, create a udev entry for
the Crazyradio and setup the permissions so that the current user can use the
radio without root permissions after restarting the computer.

### Setting udev permissions

The following steps make it possible to use the USB Radio without being root.

```
sudo groupadd plugdev
sudo usermod -a -G plugdev <username>
```

Create a file named ```/etc/udev/rules.d/99-crazyradio.rules``` and add the
following:
```
SUBSYSTEM=="usb", ATTRS{idVendor}=="1915", ATTRS{idProduct}=="7777", MODE="0664", GROUP="plugdev"
```

To connect Crazyflie 2.0 via usb, create a file name ```/etc/udev/rules.d/99-crazyflie.rules``` and add the following:
```
SUBSYSTEM=="usb", ATTRS{idVendor}=="0483", ATTRS{idProduct}=="5740", MODE="0664", GROUP="plugdev"
```

[cfclient]: https://www.github.com/bitcraze/crazyflie-clients-python


Contribute
----------

Everyone is encouraged to contribute to the CrazyFlie library by forking the Github repository and making a pull request or opening an issue.
