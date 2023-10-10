---
title: "Step-by-Step: Connecting, logging and parameters"
page_id: sbs_connect_log_param
redirect:  /step-by-step/connect_log_param/
---

On this step by step guide we will show you how to connect to your Crazyflie through the Crazyflie python library by a python script. This is the starting point for developing for the Crazyflie for off-board enabled flight.

## Prerequisites

We will assume that you already know this before you start with the tutorial:

* Some basic experience with python
* Followed the [crazyflie getting started guide](https://www.bitcraze.io/documentation/tutorials/getting-started-with-crazyflie-2-x/).
* Able to connect the crazyflie to the CFClient and look at the log tabs and parameters (here is a [userguide](https://www.bitcraze.io/documentation/repository/crazyflie-clients-python/master/userguides/userguide_client/)).


### Install the cflib

Make sure that you have [python3](https://www.python.org), which should contain pip3. In a terminal please write the following:

`pip3 install cflib`

This should have been installed if you installed the cfclient already (on a linux system), but it is always good to double check this :)

## Step 1. Connecting with the crazyflie

### Begin the python script

Open up a python script anywhere that is convenient for you. We use Visual Studio code ourselves but you can use the Python editor IDLE3 if you want.

* For python editor: select file->new
* For VS code: select file-> new file

You can call it `connect_log_param.py` (that is what we are using in this tutorial)

Then you would need to start with the following standard python libraries.

```python
import logging
import time
```

then you need to import the libraries for cflib:

```python
import cflib.crtp
from cflib.crazyflie import Crazyflie
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from cflib.utils import uri_helper
```

* The cflib.crtp module is for scanning for Crazyflies instances.
* The Crazyflie class is used to easily connect/send/receive data
from a Crazyflie.
* The synCrazyflie class is a wrapper around the "normal" Crazyflie
class. It handles the asynchronous nature of the Crazyflie API and turns it
into blocking function.

### URI of the Crazyflie

After these imports, start the script with:

```python
# URI to the Crazyflie to connect to
uri = uri_helper.uri_from_env(default='radio://0/80/2M/E7E7E7E7E7')
```

This is the radio uri of the crazyflie, it can be set by setting the environment variable `CFLIB_URI`, if not set it uses the default. It should be probably fine but if you do not know what the uri of your Crazyfie is you can check that with an usb cable and looking at the config ([here](https://www.bitcraze.io/documentation/repository/crazyflie-clients-python/master/userguides/userguide_client/#firmware-configuration) are the instructions)

### Main

Write the following in the script:
```python
if __name__ == '__main__':
    # Initialize the low-level drivers
    cflib.crtp.init_drivers()

    with SyncCrazyflie(uri, cf=Crazyflie(rw_cache='./cache')) as scf:

        simple_connect()
```

The `syncCrazyflie` will create a synchronous Crazyflie instance with the specified link_uri. As you can see we are currently calling an non-existing function, so you will need to make that function first before you run the script.

### Function for connecting with the crazyflie

Start a function above the main function (but below the URI) which you call simple connect:

```python
def simple_connect():

    print("Yeah, I'm connected! :D")
    time.sleep(3)
    print("Now I will disconnect :'(")
```



### Run the script

Now run the script in your terminal:


`python3 connect_log_param.py`

You are supposed to see the following in the terminal:
```python
Yeah, I'm connected! :D
Now I will disconnect :'(
```


The script connected with your Crazyflie, synced and disconnected after a few seconds. You can see that the M4 LED is flashing yellow, which means that the Crazyflie is connected to the script, but as soon as it leaves the `simple_connect()` function, the LED turns of. The Crazyflie is no longer connected

Not super exciting stuff yet but it is a great start! It is also a good test if everything is correctly configured on your system.


If you are getting an error, retrace your steps or check if your code matches the entire code underneath here. Also make sure your Crazyflie is on and your crazyradio PA connected to you computer, and that the Crazyflie is not connected to anything else (like the cfclient). If everything is peachy, please continue to the next part!

```python
import logging
import time

import cflib.crtp
from cflib.crazyflie import Crazyflie
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie

# URI to the Crazyflie to connect to
uri = 'radio://0/80/2M/E7E7E7E7E7'

def simple_connect():

    print("Yeah, I'm connected! :D")
    time.sleep(3)
    print("Now I will disconnect :'(")

if __name__ == '__main__':
    # Initialize the low-level drivers
    cflib.crtp.init_drivers()

    with SyncCrazyflie(uri, cf=Crazyflie(rw_cache='./cache')) as scf:

        simple_connect()
```

## Step 2a. Logging (synchronous)



Alright, now taking a step up. We will now add to the script means to read out logging variables!



### More imports

Now we need to add several imports on the top of the script connect_log_param.py

 ```python
 ...
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie

from cflib.crazyflie.log import LogConfig
from cflib.crazyflie.syncLogger import SyncLogger
 ```
 * LogConfig class is a representation of one log configuration that enables logging
    from the Crazyflie
 * The SyncLogger class provides synchronous access to log data from the Crazyflie.

Also add the following underneath URI

```python
# Only output errors from the logging framework
logging.basicConfig(level=logging.ERROR)
```

### Add logging config

Now we are going to define the logging configuration. So add `lg_stab` in the `__main__` function :
 ```python
 ...
    cflib.crtp.init_drivers()

    lg_stab = LogConfig(name='Stabilizer', period_in_ms=10)
    lg_stab.add_variable('stabilizer.roll', 'float')
    lg_stab.add_variable('stabilizer.pitch', 'float')
    lg_stab.add_variable('stabilizer.yaw', 'float')

    with SyncCrazyflie(uri, cf=Crazyflie(rw_cache='./cache')) as scf:
    ...

 ```

Here you will add the logs variables you would like to read out. If you are unsure how your variable is called, this can be checked by connecting to Crazyflie to the cfclient and look at the log TOC tab. If the variables don't match, you get a `KeyError` (more on that later.)


### Make the logging function

Use the same connect_log_param.py script, and add the following function above `simple_connect()` and underneath URI:
 ```python
def simple_log(scf, logconf):

 ```
Notice that now you will need to include the SyncCrazyflie instance (`scf`) and the logging configuration.

Now the logging instances will be inserted by adding the following after you configured the lg_stab:
 ```python
    with SyncLogger(scf, lg_stab) as logger:

        for log_entry in logger:

            timestamp = log_entry[0]
            data = log_entry[1]
            logconf_name = log_entry[2]

            print('[%d][%s]: %s' % (timestamp, logconf_name, data))

            break

 ```

### Test the script:

First change the `simple_connect()` in _main_ in `simple_log(scf, lg_stab)`. Now run the script (`python3 connect_log_param.py`) like before.

If everything is fine it should continuously print the logging variables, like this:

`[1486704][<cflib.crazyflie.log.LogConfig object at 0x7ffb3384a1d0>]: {'stabilizer.roll': -0.054723262786865234, 'stabilizer.pitch': 0.006269464734941721, 'stabilizer.yaw': -0.008503230288624763}`


If you want to continuously receive the messages in the for loop, remove the `break`. You can stop the script with _ctrl+c_

If you are getting errors, check if your script corresponds with the full code:
 ```python
import logging
import time

import cflib.crtp
from cflib.crazyflie import Crazyflie
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie

from cflib.crazyflie.log import LogConfig
from cflib.crazyflie.syncLogger import SyncLogger

# URI to the Crazyflie to connect to
uri = 'radio://0/80/2M/E7E7E7E7E7'

# Only output errors from the logging framework
logging.basicConfig(level=logging.ERROR)

def simple_log(scf, logconf):

    with SyncLogger(scf, logconf) as logger:

        for log_entry in logger:

            timestamp = log_entry[0]
            data = log_entry[1]
            logconf_name = log_entry[2]

            print('[%d][%s]: %s' % (timestamp, logconf_name, data))

            break
...

if __name__ == '__main__':
    # Initialize the low-level drivers
    cflib.crtp.init_drivers()

    lg_stab = LogConfig(name='Stabilizer', period_in_ms=10)
    lg_stab.add_variable('stabilizer.roll', 'float')
    lg_stab.add_variable('stabilizer.pitch', 'float')
    lg_stab.add_variable('stabilizer.yaw', 'float')

    with SyncCrazyflie(uri, cf=Crazyflie(rw_cache='./cache')) as scf:

        # simple_connect()

        simple_log(scf, lg_stab)

 ```

## Step 2b. Logging (Asynchronous)

The logging we have showed you before was in a synchronous manner, so it reads out the logging in the function directly in the loop. Eventhough the SyncLogger does not take much time in general, for application purposes it might be preferred to receive the logging variables separately from this function, in a callback independently of the main loop-rate.

Here we will explain how this asynchronous logging can be set up in the script.

### Start a new function

Above `def simple_log(..)`, begin a new function:

```python
def simple_log_async(scf, logconf):
    cf = scf.cf
    cf.log.add_config(logconf)
```

Here you add the logging configuration to to the logging framework of the Crazyflie. It will check if the log configuration is part of the TOC, which is a list of all the logging variables defined in the Crazyflie. You can test this out by changing one of the `lg_stab` variables to a completely bogus name like `'not.real'`. In this case you would receive the following message:

`KeyError: 'Variable not.real not in TOC'`

### Add a callback function

First we will make the callback function like follows:
```python
def log_stab_callback(timestamp, data, logconf):
    print('[%d][%s]: %s' % (timestamp, logconf.name, data))
```

This callback will be called once the log variables have received it and prints the contents. The callback function added to the logging framework by adding it to the log config in `simple_log_async(..)`:

```python
    logconf.data_received_cb.add_callback(log_stab_callback)
```

Then the log configuration would need to be started manually, and then stopped after a few seconds:

```python
    logconf.start()
    time.sleep(5)
    logconf.stop()
```

## Run the script

Make sure to replace the `simple_log(...)` to `simple_log_async(...)` in the `__main__` function. Run the script with `python3 connect_log_param.py` in a terminal and you should see several messages of the following:

`[18101][Stabilizer]: {'stabilizer.roll': -174.58396911621094, 'stabilizer.pitch': 42.82120132446289, 'stabilizer.yaw': 166.29837036132812}`

If something went wrong, check if your script corresponds to the this:

```python
import logging
import time

import cflib.crtp
from cflib.crazyflie import Crazyflie
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie

from cflib.crazyflie.log import LogConfig
from cflib.crazyflie.syncLogger import SyncLogger

# URI to the Crazyflie to connect to
uri = 'radio://0/80/2M/E7E7E7E7E7'

# Only output errors from the logging framework
logging.basicConfig(level=logging.ERROR)

def log_stab_callback(timestamp, data, logconf):
    print('[%d][%s]: %s' % (timestamp, logconf.name, data))

def simple_log_async(scf, logconf):
    cf = scf.cf
    cf.log.add_config(logconf)
    logconf.data_received_cb.add_callback(log_stab_callback)
    logconf.start()
    time.sleep(5)
    logconf.stop()

(...)

if __name__ == '__main__':
    # Initialize the low-level drivers
    cflib.crtp.init_drivers()

    lg_stab = LogConfig(name='Stabilizer', period_in_ms=10)
    lg_stab.add_variable('stabilizer.roll', 'float')
    lg_stab.add_variable('stabilizer.pitch', 'float')
    lg_stab.add_variable('stabilizer.yaw', 'float')

    with SyncCrazyflie(uri, cf=Crazyflie(rw_cache='./cache')) as scf:

        simple_log_async(scf, lg_stab)
```

## Step 3. Parameters

Next to logging variables, it is possible to read and set parameters settings. That can be done within the cfclient, but here we will look at how we can change the state estimator method in the python script.

First add the group parameter name just above `with SyncCrazyflie(...` in `__main__`.

```python
    group = "stabilizer"
    name = "estimator"
```

### Start the function

Start the following function above `def log_stab_callback(...)`:

```python
def simple_param_async(scf, groupstr, namestr):
    cf = scf.cf
    full_name = groupstr+ "." +namestr
```

### Add the callback for parameters

In a similar way as in the previous section for the Async logging, we are going to make a callback function for the parameters. Add the callback function above `def simple_param_async`:

```python
def param_stab_est_callback(name, value):
    print('The crazyflie has parameter ' + name + ' set at number: ' + value)
```

Then add the following to the `def simple_param_async(...)` function:
```python
    cf.param.add_update_callback(group=groupstr, name=namestr,
                                           cb=param_stab_est_callback)
    time.sleep(1)

```
The sleep function is to give the script a bit more time to wait for the Crazyflies response and not lose the connection immediately.

If you would like to test out the script now already, replace `simple_log_async(...)` with `simple_param_async(scf, group, name)` and run the script. You can see that it will print out the variable name and value:
`The crazyflie has parameter stabilizer.estimator set at number: 1`


### Set a parameter

Now we will set a variable in a parameter. Add the following to the `simple_param_async(...)` function:

```python
    cf.param.set_value(full_name,2)
```

If you would run the script now you will also get this message:
`The crazyflie has parameter stabilizer.estimator set at number: 2`

This means that the Crazyflie has changed the parameter value to 2, which is another methods it uses for state estimation. This can also be done to change the color on the ledring, or to initiate the highlevel commander.

What it can't do is to set a Read Only (RO) parameter, only Read Write (RW) parameters, which can be checked by the parameter TOC in the CFclient. You can check this by changing the parameter name to group `'CPU' ` and name `flash'`. Then you will get the following error:

`AttributeError: cpu.flash is read-only!`

### Finishing and running the script

It is usually good practice to put the parameter setting back to where it came from, since after disconnecting the Crazyflie, the parameter will still be set. Only after physically restarting the Crazyflie the parameter will reset to its default setting as defined in the firmware.

So finish the `simple_param_async(...)` function by adding the next few lines:
```python
    cf.param.set_value(full_name,1)
    time.sleep(1)
```
Make sure the right function is in `__main__`. Check if your script corresponds with the code:

```python
import logging
import time

import cflib.crtp
from cflib.crazyflie import Crazyflie
from cflib.crazyflie.log import LogConfig
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from cflib.crazyflie.syncLogger import SyncLogger

# URI to the Crazyflie to connect to
uri = 'radio://0/80/2M/E7E7E7E7E7'

# Only output errors from the logging framework
logging.basicConfig(level=logging.ERROR)


def param_stab_est_callback(name, value):
    print('The crazyflie has parameter ' + name + ' set at number: ' + value)


def simple_param_async(scf, groupstr, namestr):
    cf = scf.cf
    full_name = groupstr + '.' + namestr

    cf.param.add_update_callback(group=groupstr, name=namestr,
                                 cb=param_stab_est_callback)
    time.sleep(1)
    cf.param.set_value(full_name, 2)
    time.sleep(1)
    cf.param.set_value(full_name, 1)
    time.sleep(1)


def log_stab_callback(timestamp, data, logconf):
    ...
def simple_log_async(scf, logconf):
    ...
def simple_log(scf, logconf):
    ...
def simple_connect():
    ...

if __name__ == '__main__':
    # Initialize the low-level drivers
    cflib.crtp.init_drivers()

    lg_stab = LogConfig(name='Stabilizer', period_in_ms=10)
    lg_stab.add_variable('stabilizer.roll', 'float')
    lg_stab.add_variable('stabilizer.pitch', 'float')
    lg_stab.add_variable('stabilizer.yaw', 'float')

    group = 'stabilizer'
    name = 'estimator'

    with SyncCrazyflie(uri, cf=Crazyflie(rw_cache='./cache')) as scf:
        simple_param_async(scf, group, name)
```



Run the script with `python3 connect_log_param.py` in a terminal and you should see the following:

```python
The crazyflie has parameter stabilizer.estimator set at number: 1
The crazyflie has parameter stabilizer.estimator set at number: 2
The crazyflie has parameter stabilizer.estimator set at number: 1
```

You're done! The full code of this tutorial can be found in the example/step-by-step/ folder.


## What's next?


 Now you know how to connect to the Crazyflie and how to retrieve the parameters and logging variables through a python script. The next step is to make the Crazyflie fly by giving it setpoints which is one step closer to making your own application!

 Go to the [next tutorial](/docs/user-guides/sbs_motion_commander.md) about the motion commander.
