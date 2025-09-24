---
title: Installation
page_id: install
---

## Requirements

This project requires Python 3.10+.

> **Recommendation**: Use a Python virtual environment to isolate dependencies. See the [official Python venv documentation](https://docs.python.org/3/library/venv.html) for setup instructions.

## Platform Prerequisites

### Ubuntu/Linux

The Crazyradio is easily recognized on Linux, but you need to set up udev permissions. See the [USB permission instructions](/docs/installation/usb_permissions.md) to configure udev on Ubuntu/Linux.

> **Note for Ubuntu 20.04 users**: Use `pip3` instead of `pip` in all installation commands below.

### Windows

Install the Crazyradio drivers using the [Zadig instructions](https://www.bitcraze.io/documentation/repository/crazyradio-firmware/master/building/usbwindows/).

If you're using Python 3.13, you need to install [Visual Studio](https://visualstudio.microsoft.com/downloads/). During the installation process, you only need to select the Desktop Development with C++ workload in the Visual Studio Installer.

### macOS

For Python 3.12+ on macOS, you need to install libusb using Homebrew:
```bash
$ brew install libusb
```

If your Homebrew installation is in a non-default location, you might need to link the libusb library:
```bash
$ export DYLD_LIBRARY_PATH="YOUR_HOMEBREW_PATH/lib:$DYLD_LIBRARY_PATH"
```

## Installation Methods

### From PyPI (Recommended)

```bash
pip install cflib
```

### From Source (Development)

#### Clone the repository
```bash
git clone https://github.com/bitcraze/crazyflie-lib-python.git
cd crazyflie-lib-python
```

#### Install cflib from source
```bash
pip install -e .
```

#### Uninstall cflib
```bash
pip uninstall cflib
```

## Development Tools (Optional)

### Pre-commit hooks
If you want help maintaining Python coding standards, you can install hooks that verify your style at commit time:

```bash
pip install pre-commit
cd crazyflie-lib-python
pre-commit install
pre-commit run --all-files
```

This will run the lint checkers defined in `.pre-commit-config-yaml` on your proposed changes.

### Testing with the Toolbelt

For information and installation of the [toolbelt](https://github.com/bitcraze/toolbelt):

* Check to see if you pass tests: `tb test`
* Check to see if you pass style guidelines: `tb verify`

**Note**: The toolbelt is an optional way of running tests and reduces the work needed to maintain your Python environment.
