---
title: Installing from source
page_id: install_from_source
---
### Developing for the cfclient
* [Fork the cflib](https://help.github.com/articles/fork-a-repo/)
* [Clone the cflib](https://help.github.com/articles/cloning-a-repository/), `git clone git@github.com:YOUR-USERNAME/crazyflie-lib-python.git`
* [Install the cflib in editable mode](http://pip-python3.readthedocs.org/en/latest/reference/pip_install.html?highlight=editable#editable-installs), `pip install -e path/to/cflib`


* [Uninstall the cflib if you don't want it any more](http://pip-python3.readthedocs.org/en/latest/reference/pip_uninstall.html), `pip uninstall cflib`

Note: If you are developing for the [cfclient][cfclient] you must use python3. On Ubuntu (16.04, 18.08) use `pip3` instead of `pip`.

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
Install dependencies required by the lib: `pip install -r requirements.txt`

To verify the installation, connect the crazyflie and run an example: `python examples/basiclog`

#### Install serial driver dependencies

To use the serial driver, pyserial must be installed: `pip install pyserial`
