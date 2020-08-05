---
title: Testing
page_id: testing
---

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
