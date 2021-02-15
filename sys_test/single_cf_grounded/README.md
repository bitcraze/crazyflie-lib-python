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
python3 test_powerswitch.py
```

A concrete test case, e.g.:

```
python3 test_powerswitch.py TestPowerSwitch.test_reboot
```