---
title: "Step-by-Step: Swarm Interface"
page_id: sbs_swarm_interface
---

Here we will go through step-by-step how to interface with a swarm of crazyflies and make all the copters of the swarm hover and fly simultaneously in a square shape using the `Swarm()` class of the cflib.For this tutorial you will need a swarm (2 or more) of crazyflies with the latest firmware version installed and a global positioning system (Lighthouse, Loco or MoCap) that is able to provide data for the position estimation of the crazyflies. You can also use the Flowdeck but keep in mind that you should command relative movements of each Crazyflie and due to its nature it may lead to accumulative errors and unexpected behavior over time.

## Prerequisites

We will assume that you already know this before you start with the tutorial:

* Some basic experience with python
* Followed the [crazyflie getting started guide](https://www.bitcraze.io/documentation/tutorials/getting-started-with-crazyflie-2-x/)
* Read the [high level commander](https://www.bitcraze.io/documentation/repository/crazyflie-lib-python/master/api/cflib/crazyflie/high_level_commander/), [swarm](https://www.bitcraze.io/documentation/repository/crazyflie-lib-python/master/api/cflib/crazyflie/swarm/) and [SyncCrazyflie](https://www.bitcraze.io/documentation/repository/crazyflie-lib-python/master/api/cflib/crazyflie/syncCrazyflie/) documentation .


## Get the script started

Since you should have installed cflib in the previous step by step tutorial, you are all ready to got now. Open up a new python script called `swarm_rectangle.py`. First you will start by adding the following import to the script:

```python
import time

import cflib.crtp
from cflib.crazyflie.swarm import CachedCfFactory
from cflib.crazyflie.swarm import Swarm

uris = {
    'radio://0/20/2M/E7E7E7E701',
    'radio://0/20/2M/E7E7E7E702',
    'radio://0/20/2M/E7E7E7E703',
    'radio://0/20/2M/E7E7E7E704',
    # Add more URIs if you want more copters in the swarm
}

if __name__ == '__main__':
    cflib.crtp.init_drivers()
    factory = CachedCfFactory(rw_cache='./cache')
    with Swarm(uris, factory=factory) as swarm:
```

This will import all the necessary modules and open the necessary links for communication with all the Crazyflies of the swarms. `Swarm` is a wrapper class which facilitates the execution of functions given by the user for each copter and can execute them in parallel or sequentially. Each Crazyflie is treated as a `SyncCrazyflie` instance and as the first argument in swarm wide actions. There is no need to worry about threads since they are handled internally. To reduce connection time,the factory is chosen to be instance of the `CachedCfFactory` class that will cache the Crazyflie objects in the `./cache` directory.

The radio addresses of the copters are defined in the `uris` list and you can add more if you want to.

## Step 1: Light Check

In order to verify everything is setup and working properly a light check will be performed. During this check, all the copters will light up red for a short period of time and then return to normal.
This is achieved by setting the parameter `led.bitmask` to 255 which results to all the LED's of each copter light up simultaneously.

Add the helper functions `activate_led_bit_mask`,`deactivate_led_bit_mask` and the function`light_check` above `__main__`:
```python
def activate_led_bit_mask(scf):
    scf.cf.param.set_value('led.bitmask', 255)

def deactivate_led_bit_mask(scf):
    scf.cf.param.set_value('led.bitmask', 0)

def light_check(scf):
    activateBitMask(scf)
    time.sleep(2)
    deactivateBitMask(scf)
```
`light_check` will light up a copter red for 2 seconds and then return them to normal.

Below `... Swarm(...)`  in `__main__`, execute the light check for each copter:

```python
    swarm.parallel_safe(light_check)
```
The `light_check()` is going to be called through the `parallel_safe()` method which will execute it for for all Crazyflies in the swarm, in parallel. One thread per Crazyflie is started to execute the function. The threads are joined at the end and if one or more of the threads raised an exception this function will also raise an exception.

```python
import time

import cflib.crtp
from cflib.crazyflie.swarm import CachedCfFactory
from cflib.crazyflie.swarm import Swarm


def activate_led_bit_mask(scf):
    scf.cf.param.set_value('led.bitmask', 255)

def deactivate_led_bit_mask(scf):
    scf.cf.param.set_value('led.bitmask', 0)

def light_check(scf):
    activate_led_bit_mask(scf)
    time.sleep(2)
    deactivate_led_bit_mask(scf)
    time.sleep(2)


uris = {
    'radio://0/20/2M/E7E7E7E701',
    'radio://0/20/2M/E7E7E7E702',
    'radio://0/20/2M/E7E7E7E703',
    'radio://0/20/2M/E7E7E7E704',
    # Add more URIs if you want more copters in the swarm
}

if __name__ == '__main__':
    cflib.crtp.init_drivers()
    factory = CachedCfFactory(rw_cache='./cache')
    with Swarm(uris, factory=factory) as swarm:
        swarm.parallel_safe(light_check)

```
If everything is working properly, you can move to the next step .

## Step 2: Security Before Flying
Before executing any take off and flight manoeuvres, the copters need to make sure that they have a precise enough position estimation. Otherwise it will take off anyway and it is very likely to crash. This is done through `reset_estimators()` by resetting the internal position estimator of each copter and waiting until the variance of the position estimation drops below a certain threshold.
```python
with Swarm(uris, factory=factory) as swarm:
        swarm.parallel_safe(lightCheck)
        swarm.reset_estimators()
```

## Step 3: Taking off and Landing Sequentially
Now we are going to execute the fist take off and landing using the high level commander. The high level commander (more information [here](https://www.bitcraze.io/documentation/repository/crazyflie-firmware/master/functional-areas/sensor-to-control/commanders_setpoints/#high-level-commander)) is a class that handles all the high level commands like takeoff, landing, hover, go to position and others. The high level commander is usually preferred since it needs less communication and provides more autonomy on the Crazyflie. It is always on, but just in a lower priority so you just need to execute the take off and land commands through the below functions:
```python
def take_off(scf):
    commander= scf.cf.high_level_commander

    commander.takeoff(1.0, 2.0)
    time.sleep(3)

def land(scf):
    commander= scf.cf.high_level_commander

    commander.land(0.0, 2.0)
    time.sleep(2)

    commander.stop()

def hover_sequence(scf):
    take_off(scf)
    land(scf)
```

Initially , we want only one copter at a time executing the hover_sequence so it is going to be called through the `sequential()` method of the `Swarm` in the following way:

```python
swarm.sequential(hover_sequence)
```
Leading to the following code:

```python
import time

import cflib.crtp
from cflib.crazyflie.swarm import CachedCfFactory
from cflib.crazyflie.swarm import Swarm


def activate_led_bit_mask(scf):
    scf.cf.param.set_value('led.bitmask', 255)

def deactivate_led_bit_mask(scf):
    scf.cf.param.set_value('led.bitmask', 0)

def light_check(scf):
    activateBitMask(scf)
    time.sleep(2)
    deactivateBitMask(scf)
    time.sleep(2)

def take_off(scf):
    commander= scf.cf.high_level_commander

    commander.takeoff(1.0, 2.0)
    time.sleep(3)

def land(scf):
    commander= scf.cf.high_level_commander

    commander.land(0.0, 2.0)
    time.sleep(2)

    commander.stop()

def hover_sequence(scf):
    take_off(scf)
    land(scf)

uris = {
    'radio://0/20/2M/E7E7E7E701',
    'radio://0/20/2M/E7E7E7E702',
    'radio://0/20/2M/E7E7E7E703',
    'radio://0/20/2M/E7E7E7E704',
    # Add more URIs if you want more copters in the swarm
}

if __name__ == '__main__':
    cflib.crtp.init_drivers()
    factory = CachedCfFactory(rw_cache='./cache')
    with Swarm(uris, factory=factory) as swarm:
        print('Connected to  Crazyflies')
        swarm.parallel_safe(lightCheck)
        swarm.reset_estimators()

        swarm.sequential(hover_sequence)
```
After executing it you will see all copters performing the light check and then each copter take off , hover and land. This process is repeated for all copters in the swarm.

## Step 4: Taking off and Landing in Sync
If you want to take off and land in sync, you can use the `parallel_safe()` method of the `Swarm` class.

```python
    swarm.parallel_safe(hover_sequence)
```

Now the same action is happening but for all the copters in parallel.

## Step 5: Performing a square shape flight
To make the swarm fly in a square shape, we will use the go_to method of the high level commander. Each copter executes 4 relative movements to its current position covering a square shape.

```python
def run_square_sequence(scf):
    box_size = 1
    flight_time = 2

    commander= scf.cf.high_level_commander

    commander.go_to(box_size, 0, 0, 0, flight_time, relative=True)
    time.sleep(flight_time)

    commander.go_to(0, box_size, 0, 0, flight_time, relative=True)
    time.sleep(flight_time)

    commander.go_to(-box_size, 0, 0, 0, flight_time, relative=True)
    time.sleep(flight_time)

    commander.go_to(0, -box_size, 0, 0, flight_time, relative=True)
    time.sleep(flight_time)
```
Keep in mind that the `go_to()` command does not block the code so you have to wait as long as the flight time of each movement to continue to the next one.

Since we want these maneuvers to be synchronized, the `parallel_safe()` method is chosen to execute the sequence, in similar fashion with the above steps. You can include the sequence execution in the main code of the swarm in the following way:

```python
    swarm.parallel_safe(take_off)
    swarm.parallel_safe(run_square_sequence)
    swarm.parallel_safe(land)
```
Make sure that your script looks similar to the following and execute it:

```python
import time

import cflib.crtp
from cflib.crazyflie.swarm import CachedCfFactory
from cflib.crazyflie.swarm import Swarm


def activate_led_bit_mask(scf):
    scf.cf.param.set_value('led.bitmask', 255)

def deactivate_led_bit_mask(scf):
    scf.cf.param.set_value('led.bitmask', 0)

def light_check(scf):
    ...

def take_off(scf):
    ...

def land(scf):
    ...

def run_square_sequence(scf: SyncCrazyflie):
    ...

uris = {
    'radio://0/20/2M/E7E7E7E701',
    'radio://0/20/2M/E7E7E7E702',
    'radio://0/20/2M/E7E7E7E703',
    'radio://0/20/2M/E7E7E7E704',
    # Add more URIs if you want more copters in the swarm
}

if __name__ == '__main__':
    cflib.crtp.init_drivers()
    factory = CachedCfFactory(rw_cache='./cache')
    with Swarm(uris, factory=factory) as swarm:
        print('Connected to  Crazyflies')
        swarm.parallel_safe(light_check)
        swarm.reset_estimators()

        swarm.parallel_safe(take_off)
        swarm.parallel_safe(run_square_sequence)
        swarm.parallel_safe(land)
```

## Step 6: Performing a  flight with different arguments
You can also feed different arguments to each Crazyflie in the swarm. This can be done by providing a dictionary `args_dict` to the `parallel_safe()`,`parallel()` and `sequential()` methods following the below format.

```python
args_dict = {
    URI0: [optional_param0_cf0, optional_param1_cf0],
    URI1: [optional_param0_cf1, optional_param1_cf1],
    ...
}
```

where the key is the radio address of the copter and the value is a list of optional arguments. In this way you can differentiate the behavior of each copter and execute different actions based on the copter and its particular parameters.


In this example, the copters will be placed in a square shape as shown below (pay attention to the order of the Crazyflies) and each one of them will execute different relative movements.


```python
# The layout of the positions (1m apart from each other):
#   <------ 1 m ----->
#   0                1
#          ^              ^
#          |Y             |
#          |              |
#          +------> X    1 m
#                         |
#                         |
#   3               2     .


h = 0.0 # remain constant height similar to take off height
x0, y0 = +1.0, +1.0
x1, y1 = -1.0, -1.0

#    x   y   z  time
sequence0 = [
    (x1, y0, h, 3.0),
    (x0, y1, h, 3.0),
    (x0,  0, h, 3.0),
]

sequence1 = [
    (x0, y0, h, 3.0),
    (x1, y1, h, 3.0),
    (.0, y1, h, 3.0),
]

sequence2 = [
    (x0, y1, h, 3.0),
    (x1, y0, h, 3.0),
    (x1,  0, h, 3.0),
]

sequence3 = [
    (x1, y1, h, 3.0),
    (x0, y0, h, 3.0),
    (.0, y0, h, 3.0),
]

seq_args = {
    uris[0]: [sequence0],
    uris[1]: [sequence1],
    uris[2]: [sequence2],
    uris[3]: [sequence3],
}

def run_sequence(scf: SyncCrazyflie, sequence):
    cf = scf.cf

    for arguments in sequence:
        commander = scf.cf.high_level_commander

        x, y, z = arguments[0], arguments[1], arguments[2]
        duration = arguments[3]

        print('Setting position {} to cf {}'.format((x, y, z), cf.link_uri))
        commander.go_to(x, y, z, 0, duration, relative=True)
        time.sleep(duration)
```

And in the main code of the swarm, you can execute the sequence as follows:

```python
swarm.parallel_safe(run_sequence, args_dict=seq_args)
```

The final script is going to look like this :

```python
import time

import cflib.crtp
from cflib.crazyflie.swarm import CachedCfFactory
from cflib.crazyflie.swarm import Swarm
from cflib.crazyflie import syncCrazyflie


def activate_led_bit_mask(scf):
    scf.cf.param.set_value('led.bitmask', 255)

def deactivate_led_bit_mask(scf):
    scf.cf.param.set_value('led.bitmask', 0)

def light_check(scf):
    ...

def take_off(scf):
    ...

def land(scf):
    ...


def run_square_sequence(scf):
    ...

uris = ...

# The layout of the positions (1m apart from each other):
#   <------ 1 m ----->
#   0                1
#          ^              ^
#          |Y             |
#          |              |
#          +------> X    1 m
#                         |
#                         |
#   3               2     .


h = 0.0 # remain constant height similar to take off height
x0, y0 = +1.0, +1.0
x1, y1 = -1.0, -1.0

#    x   y   z  time
sequence0 = ...

sequence1 = ...

sequence2 = ...

sequence3 = ...

seq_args = ...

def run_sequence(scf: syncCrazyflie.SyncCrazyflie, sequence):
    ...


if __name__ == '__main__':
    cflib.crtp.init_drivers()
    factory = CachedCfFactory(rw_cache='./cache')
    with Swarm(uris, factory=factory) as swarm:
        print('Connected to  Crazyflies')
        swarm.parallel_safe(light_check)

        swarm.reset_estimators()

        swarm.parallel_safe(take_off)
        swarm.parallel_safe(run_square_sequence)
        swarm.parallel_safe(run_sequence, args_dict=seq_args)
        swarm.parallel_safe(land)
```

You’re done! The full code of this tutorial can be found in the `example/step-by-step/` folder.

## What is next ?
Now you are able to control a swarm of Crazyflies and you can experiment with different behaviors for each one of them while maintaining the functionality, simplicity of working with just one since the parallelism is handled internally and you can just focus on creating awesome applications! For more examples and inspiration on the Swarm functionality, you can check out the `examples/swarm/` folder of the cflib.
