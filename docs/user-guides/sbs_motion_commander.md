---
title: "Step-by-Step: Motion Commander"
page_id: sbs_motion_commander
---

Here we will go through step-by-step how to make your crazyflie move based on a motion script. For the first part of this tutorial, you just need the crazyflie and the flowdeck. For the second part, it would be handy to have the multiranger present.

# Prerequisites

We will assume that you already know this before you start with the tutorial:

* Some basic experience with python
* Followed the [crazyflie getting started guide](https://www.bitcraze.io/documentation/tutorials/getting-started-with-crazyflie-2-x/) and [the connecting, logging and parameters tutorial](/docs/user-guides/sbs_connect_log_param.md).


# Get the script started

Since you should have installed cflib in the previous step by step tutorial, you are all ready to got now. Open up an new python script called `motion_flying.py`. First you will start by adding the following import to the script:

```
import logging
import time

import cflib.crtp
from cflib.crazyflie import Crazyflie
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from cflib.positioning.motion_commander import MotionCommander

URI = 'radio://0/80/2M/E7E7E7E7E7'

logging.basicConfig(level=logging.ERROR)

if __name__ == '__main__':

    cflib.crtp.init_drivers(enable_debug_driver=False)
    with SyncCrazyflie(URI, cf=Crazyflie(rw_cache='./cache')) as scf:
```

This probably all looks pretty familiar, except for one thing line, namely:

`from cflib.positioning.motion_commander import MotionCommander`

This imports the motion commander, which is pretty much a wrapper around the position setpoint frame work of the crazyflie. You probably have unknowingly experienced this a when trying out the assist modes in this [tutorial with the flowdeck in the cfclient](https://www.bitcraze.io/documentation/tutorials/getting-started-with-flow-deck/)

# Step 1: Security before flying

Since this tutorial won't be a table top tutorial like last time, but an actual flying one, we need to put some securities in place. The flowdeck or any other positioning deck that you are using, should be correctly attached to the crazyflie. If it is not, it will try to fly anyway without a good position estimate and for sure is going to crash.

We want to know if the deck is correctly attached before flying, therefore we will add a callback for the `"deck.bcFlow2"` parameter. Add the following line after the `...SyncCrazyflie(...)` in `__main__`
```
    with SyncCrazyflie(URI, cf=Crazyflie(rw_cache='./cache')) as scf:

        scf.cf.param.add_update_callback(group="deck", name="bcFlow2",
                                cb=param_deck_flow)
        time.sleep(1)

```

Above `__main__`, start a parameter callback function:
```
def param_deck_flow(name, value):
    global is_deck_attached
    print(value)
    if value:
        is_deck_attached = True
        print('Deck is attached!')
    else:
        is_deck_attached = False
        print('Deck is NOT attached!')
```

The `is_deck_attached` is a global variable which should be defined under `URI`

```
...
URI = 'radio://0/80/2M/E7E7E7E7E7'
is_deck_attached = False
```

Try to run the script now, and try to see if it is able to detect that the flowdeck (or any other positioning deck), is correctly attached. Also try to remove it to see if it can detect it missing as well.

This is the full script as we are:
```
import logging
import time

import cflib.crtp
from cflib.crazyflie import Crazyflie
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from cflib.positioning.motion_commander import MotionCommander

URI = 'radio://0/80/2M/E7E7E7E7E7'

is_deck_attached = False

logging.basicConfig(level=logging.ERROR)

def param_deck_flow(name, value):
    global is_deck_attached
    print(value)
    if value:
        is_deck_attached = True
        print('Deck is attached!')
    else:
        is_deck_attached = False
        print('Deck is NOT attached!')


if __name__ == '__main__':
    cflib.crtp.init_drivers(enable_debug_driver=False)

    with SyncCrazyflie(URI, cf=Crazyflie(rw_cache='./cache')) as scf:

        scf.cf.param.add_update_callback(group='deck', name='bcFlow2',
                                         cb=param_deck_flow)
        time.sleep(1)

```

# Step 2: Take off function

So now we are going to start up the SyncCrazyflie and start a function in the `__main__` function:

```
    with SyncCrazyflie(URI, cf=Crazyflie(rw_cache='./cache')) as scf:

        if is_deck_attached:
            take_off_simple(scf)
```
See that we are now using `is_deck_attached`? If this is false, the function will not be called and the crazyflie will not take off.

Now make the function `take_off_simple(..)` above `__main__`, which will contain the motion commander instance.

```
def take_off_simple(scf):
    with MotionCommander(scf) as mc:
        time.sleep(3)
```

If you run the python script, you will see the crazyflie connect and immediately take off. After flying for 3 seconds it will land again.

The reason for the crazyflie to immediately take off, is that the motion commander if intialized with a take off function that will already start sending position setpoints to the crazyflie. Once the script goes out of the instance, the motion commander instance will close with a land function.

## Changing the height

Currently the motion commander had 0.3 meters height as default but this can ofcourse be changed.

Change the  following line in `take_off_simple(...)`:
```
    with MotionCommander(scf) as mc:
        mc.up(0.3)
        time.sleep(3)
```

Run the script again. The crazyflie will first take off to 0.3 meters and then goes up for another 0.3 meters.

The same can be achieved by adjusting the default_height of the motion_commander, which is what we will do for now on in this tutorial. Remove the `mc.up(0.3)` and replace the motion commander line with
```
    with MotionCommander(scf, default_height = DEFAULT_HEIGHT) as mc:
```

Add the variable underneath `URI`:
```
DEFAULT_HEIGHT = 0.5
```


Double check if your script is the same as beneath and run it again to check


```
import logging
import time

import cflib.crtp
from cflib.crazyflie import Crazyflie
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from cflib.positioning.motion_commander import MotionCommander


URI = 'radio://0/80/2M/E7E7E7E7E7'
DEFAULT_HEIGHT = 0.5

is_deck_attached = False

logging.basicConfig(level=logging.ERROR)

def take_off_simple(scf):
    with MotionCommander(scf, default_height=DEFAULT_HEIGHT) as mc:
        time.sleep(3)
        mc.stop()

def param_deck_flow(name, value):
    ...

if __name__ == '__main__':
    cflib.crtp.init_drivers(enable_debug_driver=False)

    with SyncCrazyflie(URI, cf=Crazyflie(rw_cache='./cache')) as scf:

        scf.cf.param.add_update_callback(group='deck', name='bcFlow2',
                                         cb=param_deck_flow)
        time.sleep(1)

        if is_deck_attached:
            take_off_simple(scf)

```

# Step 3 Go Forward, Turn and Go back

So now we know how to take off, so the second step is to move in a direction! Start a new function above `def take_off_simple(scf)`:

```
def move_linear_simple(scf):
    with MotionCommander(scf, default_height=DEFAULT_HEIGHT) as mc:
        time.sleep(1)
        mc.forward(0.5)
        time.sleep(1)
        mc.back(0.5)
        time.sleep(1)
```

If you replace `take_off_simple(scf)` in `__main__` with `move_linear_simple(scf)`, try to run the script.

You will see the crazyflie take off, fly 0.5 m forward, fly backwards and land again.

Now we are going to add a turn into it. Replace the content under motion commander in `move_linear_simple(..)` with the following:

```
        time.sleep(1)
        mc.forward(0.5)
        time.sleep(1)
        mc.turn_left(180)
        time.sleep(1)
        mc.forward(0.5)
        time.sleep(1)
```

Try to run the script again. Now you can see the crazyflie take off, go forward, turn 180 degrees and go forward again to its initial position.  The `mc.back()` needed to be replaced with the forward since the motion commander sends the velocity setpoints in the __body fixed coordinated__ system. This means that the commands forward will go forward to whereever the current heading (the front) of the crazyflie points to.

Double check if your code code is still correct:

```
import logging
import time

import cflib.crtp
from cflib.crazyflie import Crazyflie
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from cflib.positioning.motion_commander import MotionCommander


URI = 'radio://0/80/2M/E7E7E7E7E7'
DEFAULT_HEIGHT = 0.5

is_deck_attached = False

logging.basicConfig(level=logging.ERROR)


def move_linear_simple(scf):
    with MotionCommander(scf, default_height=DEFAULT_HEIGHT) as mc:
        time.sleep(1)
        mc.forward(0.5)
        time.sleep(1)
        mc.turn_left(180)
        time.sleep(1)
        mc.forward(0.5)
        time.sleep(1)


def take_off_simple(scf):
    ...

def param_deck_flow(name, value):
   ...


if __name__ == '__main__':
    cflib.crtp.init_drivers(enable_debug_driver=False)

    with SyncCrazyflie(URI, cf=Crazyflie(rw_cache='./cache')) as scf:

        scf.cf.param.add_update_callback(group='deck', name='bcFlow2',
                                         cb=param_deck_flow)
        time.sleep(1)

        if is_deck_attached:
            move_linear_simple(scf)
```

# Step 4: Logging while flying

When the motion commander commands have been executed, the script stops and the crazyflie lands... however that is a bit boring. Maybe you would like for it to keep flying and responding certain elements in the mean time!

Let's integrate some logging to this as well. Add the following log config right into `__main__` under `SyncCrazyflie`


```
    lg_stab = LogConfig(name='Position', period_in_ms=10)
    lg_stab.add_variable('stateEstimate.x', 'float')
    lg_stab.add_variable('stateEstimate.y', 'float')
    cf = scf.cf
    cf.log.add_config(logconf)
    logconf.data_received_cb.add_callback(log_pos_callback)

    if is_deck_attached:
        logconf.start()

        move_linear_simple(scf)

        logconf.stop()
```

Don't forget to add `from cflib.crazyflie.log import LogConfig` at the imports (we don't need the sync logger since we are going to use the callback). Make the function `log_pos_callback` above param_deck_flow:



```
def log_pos_callback(timestamp, data, logconf):
    print(data)
```

NOW: Make global variable which is a list called `position_estimate` and fill this in in the logging callback function with the x and y position. The `data` is a dict structure.

Just double check that everything has been implemented correctly and then run the script.  You will see the same behavior as with the previous step but then with the position estimated printed at the same time.

*You can replace the print function in the callback with a plotter if you would like to try that out, like with the python lib matplotlib :)*
```
import logging
import time

import cflib.crtp
from cflib.crazyflie import Crazyflie
from cflib.crazyflie.log import LogConfig
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from cflib.positioning.motion_commander import MotionCommander


URI = 'radio://0/80/2M/E7E7E7E7E7'
DEFAULT_HEIGHT = 0.5

is_deck_attached = False

logging.basicConfig(level=logging.ERROR)

position_estimate = [0, 0]

def move_linear_simple(scf):
    with MotionCommander(scf, default_height=DEFAULT_HEIGHT) as mc:
        time.sleep(1)
        mc.forward(0.5)
        time.sleep(1)
        mc.turn_left(180)
        time.sleep(1)
        mc.forward(0.5)
        time.sleep(1)


def take_off_simple(scf):
    ...

def log_pos_callback(timestamp, data, logconf):
    print(data)
    global position_estimate
    position_estimate[0] = data['stateEstimate.x']
    position_estimate[1] = data['stateEstimate.y']


def param_deck_flow(name, value):
    ...

if __name__ == '__main__':
    cflib.crtp.init_drivers(enable_debug_driver=False)

    with SyncCrazyflie(URI, cf=Crazyflie(rw_cache='./cache')) as scf:

        scf.cf.param.add_update_callback(group='deck', name='bcFlow2',
                                         cb=param_deck_flow)
        time.sleep(1)

        logconf = LogConfig(name='Position', period_in_ms=10)
        logconf.add_variable('stateEstimate.x', 'float')
        logconf.add_variable('stateEstimate.y', 'float')
        scf.cf.log.add_config(logconf)
        logconf.data_received_cb.add_callback(log_pos_callback)

        if is_deck_attached:
            logconf.start()

            move_linear_simple(scf)
            logconf.stop()


```

# Step 5: Combine logging and motion commander

There is a reason why we put the position_estimate to catch the positions from the log, since we would like to now do something with it!

## Back and forth with limits
Lets start with a new function above `move_in_box_limit(scf)`:

```
def move_box_limit(scf):
    with MotionCommander(scf, default_height=DEFAULT_HEIGHT) as mc:

        while (1):

            time.sleep(0.1)

```

If you would run this (don't forget to replace `move_linear_simple()` in `__main__`), you see the crazyflie take off but it will stay in the air. A keyboard interrupt (ctrl+c) will stop the script and make the crazyflie land again.

Now we will add some behavior in the while loop:

```
def move_box_limit(scf):
    with MotionCommander(scf, default_height=DEFAULT_HEIGHT) as mc:
        start_forward()

        while (1):
            if position_estimate[0] > BOX_LIMIT:
                mc.start_back()
            elif position_estimate[0] < -BOX_LIMIT:
                mc.start_forward()
            time.sleep(0.1)

```

Add `BOX_LIMIT = 0.5` underneath the definition of the `DEFAULT_HEIGHT = 0.5`.

Run the script and you will see that the crazyflie will start moving back and forth until you hit ctrl+c. It changes its command based on the logging input, which is the state estimate x and y position. Once it indicates that it reached the border of the 'virtual' limit, it will change it's direction.

You probably also noticed that we are using `mc.start_back()` and `mc.start_forward()` instead of the `mc.forward(0.5)` and `mc.back(0.5)` used in the previous steps. The main difference is that the *mc.forward* and *mc.back* are **blocking** functions that won't continue the code until the distance has been reached. The *mc.start_...()* will start the crazyflie in a direction and will not stop until the `mc.stop()` is given, which is given automatically when the motion commander instance is exited. That is why this is nice functions to use in reactive scenarios like these.

```
import logging
import time

import cflib.crtp
from cflib.crazyflie import Crazyflie
from cflib.crazyflie.log import LogConfig
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from cflib.positioning.motion_commander import MotionCommander


URI = 'radio://0/80/2M/E7E7E7E7E7'
DEFAULT_HEIGHT = 0.5
BOX_LIMIT = 0.5

is_deck_attached = False

logging.basicConfig(level=logging.ERROR)

position_estimate = [0, 0]


def move_box_limit(scf):
    with MotionCommander(scf, default_height=DEFAULT_HEIGHT) as mc:
        body_x_cmd = 0.2
        body_y_cmd = 0.1
        max_vel = 0.2

        while (1):
            if position_estimate[0] > BOX_LIMIT:
                mc.start_back()
            elif position_estimate[0] < -BOX_LIMIT:
                mc.start_forward()

def move_linear_simple(scf):
    ...

def take_off_simple(scf):
    ...

def log_pos_callback(timestamp, data, logconf):
    ...

def param_deck_flow(name, value):
    ...

if __name__ == '__main__':
    cflib.crtp.init_drivers(enable_debug_driver=False)

    with SyncCrazyflie(URI, cf=Crazyflie(rw_cache='./cache')) as scf:

        scf.cf.param.add_update_callback(group='deck', name='bcFlow2',
                                         cb=param_deck_flow)
        time.sleep(1)

        logconf = LogConfig(name='Position', period_in_ms=10)
        logconf.add_variable('stateEstimate.x', 'float')
        logconf.add_variable('stateEstimate.y', 'float')
        scf.cf.log.add_config(logconf)
        logconf.data_received_cb.add_callback(log_pos_callback)

        if is_deck_attached:
            logconf.start()
            move_box_limit(scf)
            logconf.stop()
```

## Bouncing in a bounding box

Let's take it up a notch! Replace the content in the while loop with the following:
```
        body_x_cmd = 0.2;
        body_y_cmd = 0.1;
        max_vel = 0.2;

        while (1):
            if position_estimate[0] > BOX_LIMIT:
                 body_x_cmd=-max_vel
            elif position_estimate[0] < -BOX_LIMIT:
                body_x_cmd=max_vel
            if position_estimate[1] > BOX_LIMIT:
                body_y_cmd=-max_vel
            elif position_estimate[1] < -BOX_LIMIT:
                body_y_cmd=max_vel

            mc.start_linear_motion(body_x_cmd, body_y_cmd, 0)

            time.sleep(0.1)
```

This will now start a linear motion into a certain direction, and makes the Crazyflie bounce around in a virtual box of which the size is indicated by 'BOX_LIMIT'. So before you fly make sure that you pick a box_limit small enough so that it able to fit in your flying area.

**Note**: if you are using the flowdeck, it might be that the orientation of this box will seem to change. This is due to that the flowdeck is not able to provide an absolute heading estimate, which will be only based on gyroscope measurements. This will drift over time, which is accelerated if you incorporate many turns in your application. There are also reports that happens quickly when the crazyflie is still on the ground. This should not happen with MoCap or the lighthouse deck.


Check out if your code still matches the full code and run the script!
```
import logging
import time

import cflib.crtp
from cflib.crazyflie import Crazyflie
from cflib.crazyflie.log import LogConfig
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from cflib.positioning.motion_commander import MotionCommander


URI = 'radio://0/80/2M/E7E7E7E7E7'
DEFAULT_HEIGHT = 0.5
BOX_LIMIT = 0.5

is_deck_attached = False

logging.basicConfig(level=logging.ERROR)

position_estimate = [0, 0]


def move_box_limit(scf):
    with MotionCommander(scf, default_height=DEFAULT_HEIGHT) as mc:
        body_x_cmd = 0.2
        body_y_cmd = 0.1
        max_vel = 0.2

        while (1):
            #if position_estimate[0] > BOX_LIMIT:
            #    mc.start_back()
            #elif position_estimate[0] < -BOX_LIMIT:
            #    mc.start_forward()

            if position_estimate[0] > BOX_LIMIT:
                body_x_cmd = -max_vel
            elif position_estimate[0] < -BOX_LIMIT:
                body_x_cmd = max_vel
            if position_estimate[1] > BOX_LIMIT:
                body_y_cmd = -max_vel
            elif position_estimate[1] < -BOX_LIMIT:
                body_y_cmd = max_vel

            mc.start_linear_motion(body_x_cmd, body_y_cmd, 0)

            time.sleep(0.1)


def move_linear_simple(scf):
    ...

def take_off_simple(scf):
    ...

def log_pos_callback(timestamp, data, logconf):
    print(data)
    global position_estimate
    position_estimate[0] = data['stateEstimate.x']
    position_estimate[1] = data['stateEstimate.y']


def param_deck_flow(name, value):
    global is_deck_attached
    print(value)
    if value:
        is_deck_attached = True
        print('Deck is attached!')
    else:
        is_deck_attached = False
        print('Deck is NOT attached!')


if __name__ == '__main__':
    cflib.crtp.init_drivers(enable_debug_driver=False)

    with SyncCrazyflie(URI, cf=Crazyflie(rw_cache='./cache')) as scf:

        scf.cf.param.add_update_callback(group='deck', name='bcFlow2',
                                         cb=param_deck_flow)
        time.sleep(1)

        logconf = LogConfig(name='Position', period_in_ms=10)
        logconf.add_variable('stateEstimate.x', 'float')
        logconf.add_variable('stateEstimate.y', 'float')
        scf.cf.log.add_config(logconf)
        logconf.data_received_cb.add_callback(log_pos_callback)

        if is_deck_attached:
            logconf.start()
            move_box_limit(scf)
            logconf.stop()
```

You're done! The full code of this tutorial can be found in the example/step-by-step/ folder.


# What is next ?

Now you are able to send velocity commands to the Crazyflie and react upon logging and parameters variables, so one step closer to writing your own application with the Crazyflie python library! Check out the motion_commander_demo.py in the example folder of the cflib if you would like to see what the commander can do.
