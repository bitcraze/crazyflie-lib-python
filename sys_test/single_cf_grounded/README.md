# Tests for a single Crazyflie 2.X (USB & Crazyradio) without flight

## Preparation

* attach a single Crazyflie over USB
* attach a Crazyradio (PA)
* (Optional) update URI in `single_cf_grounded.py`

## Execute Tests

All tests:

```
python3 -m unittest discover . -v
```

A single test file, e.g.:

```
python3 test_power_switch.py
```

A concrete test case, e.g.:

```
python3 test_power_switch.py TestPowerSwitch.test_reboot
```

## Environment Variables

Prepend command with `USE_CFLINK=cpp` to run with cflinkcpp native link library.
