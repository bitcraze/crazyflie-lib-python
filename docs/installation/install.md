---
title: Installation
page_id: install
---

## Development
### Developing for the cflib
* [Fork the cflib](https://help.github.com/articles/fork-a-repo/)
* [Clone the cflib](https://help.github.com/articles/cloning-a-repository/), `git clone git@github.com:YOUR-USERNAME/crazyflie-lib-python.git`
* [Install the cflib in editable mode](http://pip-python3.readthedocs.org/en/latest/reference/pip_install.html?highlight=editable#editable-installs), `pip install -e path/to/cflib`


* [Uninstall the cflib if you don't want it any more](http://pip-python3.readthedocs.org/en/latest/reference/pip_uninstall.html), `pip uninstall cflib`

Note: If you are developing for the cflib you must use python3. On Ubuntu (16.04, 18.08) use `pip3` instead of `pip`.

### Linux, OSX, Windows

The following should be executed in the root of the crazyflie-lib-python file tree.

#### Virtualenv
This section contains a very short description of how to use [virtualenv (local python environment)](https://virtualenv.pypa.io/en/latest/)
with package dependencies. If you don't want to use virualenv and don't mind installing cflib dependencies system-wide
you can skip this section.

* Install virtualenv: `pip install virtualenv`
* create an environment: `virtualenv venv`
* Activate the environment: `source venv/bin/activate`


* To deactivate the virtualenv when you are done using it `deactivate`

Note: For systems that support [make](https://www.gnu.org/software/make/manual/html_node/Simple-Makefile.html), you can use `make venv` to
create an environment, activate it and install dependencies.

#### Install cflib dependencies
Install dependencies required by the lib: `pip install -r requirements.txt`. If you are planning on developing on the lib you should also run: `pip install -r requirements-dev.txt`.

To verify the installation, connect the crazyflie and run an example: `python examples/basiclog`

### Pre commit hooks
If you want some extra help with keeping to the mandated python coding style you can install hooks that verify your style at commit time. This is done by running:
```
$ pre-commit install
```
This will run the lint checkers defined in `.pre-commit-config-yaml` on your proposed changes and alert you if you need to change anything.

## Testing
### With docker and the toolbelt

For information and installation of the
[toolbelt.](https://wiki.bitcraze.io/projects:dockerbuilderimage:index)

* Check to see if you pass tests: `tb test`
* Check to see if you pass style guidelines: `tb verify`

Note: Docker and the toolbelt is an optional way of running tests and reduces the
work needed to maintain your python environment.

### Native python on Linux, OSX, Windows
 [Tox](http://tox.readthedocs.org/en/latest/) is used for native testing: `pip install tox`
* If test fails after installing tox with `pip install tox`, installing with  `sudo apt-get install tox`result a successful test run

* Test package in python3.4 `TOXENV=py34 tox`
* Test package in python3.6 `TOXENV=py36 tox`

Note: You must have the specific python versions on your machine or tests will fail. (ie. without specifying the TOXENV, `tox` runs tests for python 3.3, 3.4 and would require all python versions to be installed on the machine.)


## Platform notes

### Linux

#### Setting udev permissions

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
