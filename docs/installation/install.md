---
title: Installation
page_id: install
---

## Requirements

This project requires Python 3.10+.

To install on Python 3.13, build tools and Python development headers are required.

***NOTE: Running with python 3.13 on macOS is not officially supported***

See below sections for more platform-specific requirements.
## Install from Source
### Clone  the repository
 ```
 git clone https://github.com/bitcraze/crazyflie-lib-python.git
 ```
### Install cflib from source
 ```
 cd crazyflie-lib-python
 pip install -e .
 ```

### Uninstall cflib

 ```
pip uninstall cflib
 ```

Note: If you are developing for the cflib you must use python3. On Ubuntu (20.04+) use `pip3` instead of `pip`.

### Linux, macOS, Windows

The following should be executed in the root of the crazyflie-lib-python file tree.

#### Virtualenv
This section contains a very short description of how to use [virtualenv (local python environment)](https://virtualenv.pypa.io/en/latest/)
with package dependencies. If you don't want to use virualenv and don't mind installing cflib dependencies system-wide
you can skip this section.

* Install virtualenv: `pip install virtualenv`
* create an environment: `virtualenv venv`
* Activate the environment: `source venv/bin/activate`


* To deactivate the virtualenv when you are done using it `deactivate`

### Pre-commit hooks (Ubuntu)
If you want some extra help with keeping to the mandated Python coding style you can install hooks that verify your style at commit time. This is done by running:
```
$ pip3 install pre-commit
```
go to crazyflie-lib-python root folder and run
```
$ pre-commit install
$ pre-commit run --all-files
```
This will run the lint checkers defined in `.pre-commit-config-yaml` on your proposed changes and alert you if you need to change anything.

## Testing
### With docker and the toolbelt

For information and installation of the
[toolbelt.](https://github.com/bitcraze/toolbelt)

* Check to see if you pass tests: `tb test`
* Check to see if you pass style guidelines: `tb verify`

Note: Docker and the toolbelt is an optional way of running tests and reduces the
work needed to maintain your python environment.

## Platform notes

### Linux

With linux, the crazyradio is easily recognized, but you have to setup UDEVpermissions. Look at the [usb permission instructions](/docs/installation/usb_permissions.md) to setup udev on linux.

### Windows

Look at the [Zadig crazyradio instructions](https://www.bitcraze.io/documentation/repository/crazyradio-firmware/master/building/usbwindows/) to install crazyradio on Windows

If you're using Python 3.13, you need to install [Visual Studio](https://visualstudio.microsoft.com/downloads/). During the installation process, you only need to select the Desktop Development with C++ workload in the Visual Studio Installer.

### macOS
If you are using python 3.12 on mac you need to install libusb using homebrew.
```
$ brew install libusb
```

If your Homebrew installation is in a non default location or if you want to install libusb in some other way you
might need to link the libusb library like this;
```
$ export DYLD_LIBRARY_PATH="YOUR_HOMEBREW_PATH/lib:$DYLD_LIBRARY_PATH"
```
