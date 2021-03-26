# Tests using the Roadrunner Testrig

## Preparation

* Power Roadrunner Testrig
* attach a Crazyradio (PA) to PC
* Flash the firmware using `./cload_all.sh <path/to/firmware-tag-<version>.zip>`

## Execute Tests

All tests:

```
python3 -m unittest discover . -v
```

There is also a script in `tools/build/sys-test` that essentially does that.

A single test file, e.g.:

```
python3 test_connection.py
```

A concrete test case, e.g.:

```
python3 test_connection.py TestConnection.test_that_connection_time_scales_with_more_devices_without_cache
```
