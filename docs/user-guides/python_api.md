---
title: The Crazyflie Python API
page_id: python_api
---

In order to easily use and control the Crazyflie there\'s an library
made in Python that gives high-level functions and hides the details.
This page contains generic information about how to use this library and
the API that it implements.

If you are interested in more details look in the PyDoc in the code or:

-   Communication protocol for
    [logging](https://www.bitcraze.io/documentation/repository/crazyflie-firmware/master/functional-areas/crtp/crtp_log/) or
    [parameters](https://www.bitcraze.io/documentation/repository/crazyflie-firmware/master/functional-areas/crtp/crtp_parameters/)

## Structure of the library

The library is asynchronous and based on callbacks for events. Functions
like `open_link` will return immediately, and the callback `connected`
will be called when the link is opened. The library doesn\'t contain any
threads or locks that will keep the application running, it\'s up to the
application that is using the library to do this.

There are a few synchronous wrappers for selected classes that creates
a synchronous API by wrapping the asynchronous classes, see the
[Synchronous API section](#synchronous-api)

### Uniform Resource Identifier (URI)

All communication links are identified using an URI build up of the
following: InterfaceType://InterfaceId/InterfaceChannel/InterfaceSpeed

Currently only *radio* and *debug* interfaces are used but there\'s
ideas for more like *udp*, *serial*, *usb*, etc\...Here are some
examples:

-   \%%Radio interface, USB dongle number 0, radio channel 10 and radio
    speed 250 Kbit/s: radio://0/10/250K %%
-   Debug interface, id 0, channel 1: debug://0/1

### Variables and logging

The library supports setting up logging configurations that are used for
logging variables from the firmware. Each log configuration contains a
number of variables that should be logged as well as a time period (in
ms) of how often the data should be sent back to the host. Once the log
configuration is added to the firmware the firmware will automatically
send back the data at every period. These configurations are used in the
following way:

-   Connect to the Crazyflie (log configurations needs a TOC to work)
-   Create a log configuration that contains a number of variables to
    log and a period at which they should be logged
-   Add the log configuration. This will also validate that the log
    configuration is sane (i.e uses a supported period and all variables
    are in the TOC)
-   After checking that the configuration is valid, set up callbacks for
    the data in your application and start the log configuration
-   Each time the firmware sends data back to the host the callback will
    the called with a time-stamp and the data

There\'s a few limitations that needs to be taken into account:

-   Each packet is limited to 32bytes, which means that the data that is
    logged and the packet that is sent to set it up cannot be larger
    than this. It limits the logging to about 14 variables, but this is
    dependent on what types they are
-   The minimum period of a for a log configuration is multiples of 10ms

### Parameters

The library supports reading and writing parameters at run-time to the
firmware. This is intended to be used for data that is not continuously
being changed by the firmware, like setting regulation parameters and
reading out if the power-on self-tests passed. Parameters should only
change in the firmware when being set from the host or during start-up.
The library doesn\'t continuously update the parameter values, this
should only be done once after connecting. After each write to a
parameter the firmware will send back the updated value and this will be
forwarded to callbacks registered for reading this parameter. The
parameters should be used in the following way:

-   Register parameter updated callbacks at any time in your application
-   Connect to your Crazyflie (this will download the parameter TOC)
-   Request updates for all the parameters
-   The library will call all the callbacks registered
-   The host can now write parameters that will be forwarded to the
    firmware
-   For each write all the callbacks registered for this parameter will
    be called back

### Variable and parameter names

All names of parameters and log variables use the same structure:
`group.name`

The group should be used to bundle together logical groups, like
everything that has to do with the stabilizer should be in the group
`stabilizer`.

There\'s a limit of 28 chars in total and here are some examples:

-   stabilizer.roll
-   stabilizer.pitch
-   pm.vbat
-   imu\_tests.MPU6050
-   pid\_attitide.pitch\_kd

## Utilities

### Callbacks

All callbacks are handled using the `Caller` class that contains the
following methods:

``` {.python}
    add_callback(cb)
        """ Register cb as a new callback. Will not register duplicates. """

    remove_callback(cb)
        """ Un-register cb from the callbacks """

    call(*args)
        """ Call the callbacks registered with the arguments args """
```

### Debug driver

The library contains a special link driver, named `DebugDriver`. This
driver will emulate a Crazyflie and is used for testing of the UI and
library. Normally this will be hidden from the user except if explicitly
enabled in the configuration file. The driver supports the following:

-   Connecting a download param and log TOCs
-   Setting up log configurations and sending back fake data
-   Setting and reading parameters
-   Bootloading

There are a number of different URIs that will be returned from the
driver. These will have different functions, like always returning a
random TOC CRC to always trigger TOC downloading or failing during
connect. The driver also has support for sending back data with random
delays to trigger random re-sending by the library.

## Initiating the link drivers

Before the library can be used the link drivers have to he initialized.
This will search for available drivers and instantiate them.

``` {.python}
    init_drivers(enable_debug_driver=False)
       """ Search for and initialize link drivers. If enable_debug_driver is True then the DebugDriver will also be used."""
```

### Serial driver

The serial driver is disabled by default and has to be enabled to
be used. Enable it in the call to `init_drivers()`

``` {.python}
    init_drivers(enable_serial_driver=True)
```

## Connection- and link-callbacks

Operations on the link and connection will return directly and will call
the following callbacks when events occur:

``` {.python}
    # Called on disconnect, no matter the reason
    disconnected = Caller()
    # Called on unintentional disconnect only
    connection_lost = Caller()
    # Called when the first packet in a new link is received
    link_established = Caller()
    # Called when the user requests a connection
    connection_requested = Caller()
    # Called when the link is established and the TOCs (that are not cached)
    # have been downloaded
    connected = Caller()
    # Called if establishing of the link fails (i.e times out)
    connection_failed = Caller()
    # Called for every packet received
    packet_received = Caller()
    # Called for every packet sent
    packet_sent = Caller()
    # Called when the link driver updates the link quality measurement
    link_quality_updated = Caller()
```

To register for callbacks the following is used:

``` {.python}
    crazyflie = Crazyflie()
    crazyflie.connected.add_callback(crazyflie_connected)
```

## Finding a Crazyflie and connecting

The first thing to do is to find a Crazyflie quadcopter that we can
connect to. This is done by queuing the library that will scan all the
available interfaces (currently the debug and radio interface).

``` {.python}
    cflib.crtp.init_drivers()
    available = cflib.crtp.scan_interfaces()
    for i in available:
        print "Interface with URI [%s] found and name/comment [%s]" % (i[0], i[1])
```

Opening and closing a communication link is doing by using the Crazyflie
object:

``` {.python}
    crazyflie = Crazyflie()
    crazyflie.connected.add_callback(crazyflie_connected)
    crazyflie.open_link("radio://0/10/250K")
```

Then you can use the following to close the link again:

``` {.python}
    crazyflie.close_link()
```

## Sending control commands

The control commands are not implemented as parameters, instead they
have a special API.

``` {.python}
    send_setpoint(roll, pitch, yaw, thrust):
        """
        Send a new control set-point for roll/pitch/yaw/thust to the copter

        The arguments roll/pitch/yaw/trust is the new set-points that should
        be sent to the copter
        """
```

To send a new control set-point use the following:

``` {.python}
    roll    = 0.0
    pitch   = 0.0
    yawrate = 0
    thrust  = 0
    crazyflie.commander.send_setpoint(roll, pitch, yawrate, thrust)
```

Thrust is an integer value ranging from 10001 (next to no power) to
60000 (full power). Sending a command makes it apply for 500 ms, after
which the firmware will cut out the power. With this in mind, you need
to try and maintain a thrust level, with a tick being sent at least once
every 2 seconds. Ideally you should be sending one tick every 10 ms, for
100 commands a second. This has a nice added benefit of allowing for
very precise control.

## Parameters

The parameter framework is used to read and set parameters. This
functionality should be used when:

-   The parameter is not changed by the Crazyflie but by the client
-   The parameter is not read periodically

If this is not the case then the logging framework should be used
instead.

To set a parameter you have to the connected to the Crazyflie. A
parameter is set using:

``` {.python}
    param_name = "group.name"
    param_value = 3
    crazyflie.param.set_value(param_name, param_value)
```

The parameter reading is done using callbacks. When a parameter is
updated from the host (using the code above) the parameter will be read
back by the library and this will trigger the callbacks. Parameter
callbacks can be added at any time (you don\'t have to be connected to a
Crazyflie).

``` {.python}
    add_update_callback(group, name=None, cb=None)
        """
        Add a callback for a specific parameter name or group. If not name is specified then
        all parameters in the group will trigger the callback. This callback will be executed
        when a new value is read from the Crazyflie.
        """

    request_param_update(complete_name)
        """ Request an update of the value for the supplied parameter. """

    set_value(complete_name, value)
        """ Set the value for the supplied parameter. """
```

Here\'s an example of how to use the calls.

``` {.python}
    crazyflie.param.add_update_callback(group="group", name="name", param_updated_callback)

    def param_updated_callback(name, value):
        print "%s has value %d" % (name, value)
```

## Logging

The logging framework is used to enable the \"automatic\" sending of
variable values at specified intervals to the client. This functionality
should be used when:

-   The variable is changed by the Crazyflie and not by the client
-   The variable is updated at high rate and you want to read the value
    periodically

If this is not the case then the parameter framework should be used
instead.

The API to create and get information from LogConfig:

``` {.python}
    # Called when new logging data arrives
    data_received_cb = Caller()
    # Called when there's an error
    error_cb = Caller()
    # Called when the log configuration is confirmed to be started
    started_cb = Caller()
    # Called when the log configuration is confirmed to be added
    added_cb = Caller()

    add_variable(name, fetch_as=None)
        """Add a new variable to the configuration.

        name - Complete name of the variable in the form group.name
        fetch_as - String representation of the type the variable should be
                   fetched as (i.e uint8_t, float, FP16, etc)

        If no fetch_as type is supplied, then the stored as type will be used
        (i.e the type of the fetched variable is the same as it's stored in the
        Crazyflie)."""

    start()
        """Start the logging for this entry"""

    stop()
        """Stop the logging for this entry"""

    delete()
        """Delete this entry in the Crazyflie"""
```

The API for the log in the Crazyflie:

``` {.python}
    add_config(logconf)
        """Add a log configuration to the logging framework.

        When doing this the contents of the log configuration will be validated
        and listeners for new log configurations will be notified. When
        validating the configuration the variables are checked against the TOC
        to see that they actually exist. If they don't then the configuration
        cannot be used. Since a valid TOC is required, a Crazyflie has to be
        connected when calling this method, otherwise it will fail."""
```

To create a logging configuration the following can be used:

``` {.python}
    logconf = LogConfig(name="Logging", period_in_ms=100)
    logconf.add_variable("group1.name1", "float")
    logconf.add_variable("group1.name2", "uint8_t")
    logconf.add_variable("group2.name1", "int16_t")
```

The datatype is the transferred datatype, it will be converted from
internal type to transferred type before transfers:

-   float
-   uint8\_t and int8\_t
-   uint16\_t and int16\_t
-   uint32\_t and int32\_t
-   FP16: 16bit version of floating point, allows to pack more variable
    in one packet at the expense of precision.

The logging cannot be started until your are connected to a Crazyflie:

``` {.python}
    # Callback called when the connection is established to the Crazyflie
    def connected(link_uri):
        crazyflie.log.add_config(logconf)

        if logconf.valid:
            logconf.data_received_cb.add_callback(data_received_callback)
            logconf.error_cb.add_callback(logging_error)
            logconf.start()
        else:
            print "One or more of the variables in the configuration was not found in log TOC. No logging will be possible."

    def data_received_callback(timestamp, data, logconf):
        print "[%d][%s]: %s" % (timestamp, logconf.name, data)

    def logging_error(logconf, msg):
        print "Error when logging %s" % logconf.name
```

The values of log varibles are transferred from the Crazyflie using CRTP
packets, where all varibles belonging to one logging configuration are
transfered in the same packet. A CRTP packet has a maximum data size of
30 bytes, which sets an upper limit to the number of variables that
can be used in one logging configuration. If the desired log variables
do not fit in one logging configuration, a second cofiguration may
be added.

``` {.python}
    crazyflie.log.add_config([logconf1, logconfig2])
```

## Synchronous API

The synchronous classes are wrappers around the asynchronouse API, where the asynchronous
calls/callbacks are replaced with blocking calls. The synchronous API does not
provide the full flexibility of the asynchronous API, but is useful when writing
small scripts for logging for instance.

The synchronous API uses the python Context manager concept, that is the ```with``` keyword.
A resource is allocated when entering a ```with``` section and automatically released when
exiting it, for instance a connection or take off/landing of a Crazyflie.

### SyncCrazyflie

The SyncCrazyflie class wrapps a Crazyflie instance and mainly simplifies connect/disconnect.

Basic usage
``` {.python}
    with SyncCrazyflie(uri) as scf:
        # A Crazyflie instance is created and is now connected. If the connection failes,
        # an exception is raised.

        # The underlying crazyflie object can be accessed through the cf member
        scf.cf.param.set_value('kalman.resetEstimation', '1')

        # Do useful stuff
        # When leaving the "with" section, the connection is automatically closed
```

If some special properties are required for the underlying Crazyflie object,
a Crazyflie instance can be passed in to the SyncCrazyflie instance.

``` {.python}
    my_cf = Crazyflie(rw_cache='./cache')
    with SyncCrazyflie(uri, cf=my_cf) as scf:
        # The my_cf is now connected
        # Do useful stuff
        # When leaving the "with" section, the connection is automatically closed
```

### SyncLogger

The SyncLogger class wraps setting up, as well as starting/stopping logging. It works both for Crazyflie
and SyncCrazyflie instances. To get the log values, iterate the instance.

``` {.python}
    # Connect to a Crazyflie
    with SyncCrazyflie(uri) as scf:
        # Create a log configuration
        log_conf = LogConfig(name='myConf', period_in_ms=200)
        log_conf.add_variable('stateEstimateZ.vx', 'int16_t')

        # Start logging
        with SyncLogger(scf, log_conf) as logger:
            # Iterate the logger to get the values
            count = 0
            for log_entry in logger:
                print(log_entry)
                # Do useful stuff
                count += 1
                if (count > 10):
                    # The logging will continue until you exit the loop
                    break
            # When leaving this "with" section, the logging is automatically stopped
        # When leaving this "with" section, the connection is automatically closed
```

### MotionCommander

The MotionCommander is intended to simplify basic autonomous flight. The Crazyflie takes off
when entering the "with" section, and lands when exiting. It has functions for basic
movements that are blocking until the motion is finished.

The MotionCommander is using velocity set points and does not have a global coordinate
system, all positions are relative. It is mainly intended to be used with a Flow deck.

``` {.python}
    with SyncCrazyflie(URI) as scf:
        # We take off when the commander is created
        with MotionCommander(scf) as mc:
            # Move one meter forward
            mc.forward(1)
            # Move one meter back
            mc.back(1)
            # The Crazyflie lands when leaving this "with" section
        # When leaving this "with" section, the connection is automatically closed
```

### PositionHlCommander

The PositionHlCommander is intended to simplify basic autonomous flight. The Crazyflie takes off
when entering the "with" section, and lands when exiting. It has functions for basic
movements that are blocking until the motion is finished.

The PositionHlCommander uses the high level commander in the Crazyflie and is
based on a global coordinate system and absolute positoinins. It is inteneded
to be used with a positioning system such as LPS, the lighthouse or a mocap system.

``` {.python}
    with SyncCrazyflie(URI) as scf:
        with PositionHlCommander(scf) as pc:
            # Go to the coordinate (0, 0, 1)
            pc.go_to(0.0, 0.0, 1.0)
            # The Crazyflie lands when leaving this "with" section
        # When leaving this "with" section, the connection is automatically closed
```

## Examples

The see the example folder of the repository.
