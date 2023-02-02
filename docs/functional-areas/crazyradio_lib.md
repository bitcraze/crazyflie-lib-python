---
title: Python Crazyradio Library
page_id: crazyradio_lib 
---

The python crazyradio lib can be found in the Crazyflie python library git repos
<https://github.com/bitcraze/crazyflie-lib-python/blob/master/cflib/drivers/crazyradio.py>.
It is a single file that implements the low level Crazyradio dongle
functionalities.

Theory of operation
-------------------

The Crazyradio is configured in PTX mode which means that it will start
all communication. If a device in PRX mode is on the same address,
channel and datarate, the device will send back an ack packet that may
contains data.

       Crazyradio    Device
          _             _
          |             |
          |  Packet     |
          |------------>|
          |        Ack  |
          |<------------|
          |             |

This is an example on how to use the lib:

``` .python
import crazyradio

cr = crazyradio.Crazyradio()
cr.set_channel(90)
cr.set_data_rate(cr.DR_2MPS)

res = cr.send_packet([0xff, ])
print res.ack                   # At true if an ack has been received
print res.data                  # The ack payload data
```

API
---

### Crazyradio

#### Fields

None

#### Methods

##### [init]{.underline}(self. device=None, devid=0)

|  Name         | `_ _init_ _` (Constructor)|
|  -------------| ------------------------------------------------|
|  Parameters   | (USBDevice) device, (int) devid|
|  Returns      | None|
|  Description  | Initialize the Crazyradio object. If device is not specified, a list of available Crazyradio is made and devId selects the Crazyradio used (by default the first one)|

##### close(self)

|  Name         | `close`|
|  -------------| --------------------------------------------------------------------|
|  Parameters   | None|
|  Returns      | None|
|  Description  | Close the USB device. Should be called before closing the program.|

##### set\_channel(self, channel)

 | Name         | `set_channel` |
 | -------------| ---------------------------------------------------------------------|
 | Parameters   | (int) channel |
 | Returns      | None |
 | Description  | Set the Crazyradio channel. Channel must be between 0 and 125. Channels are spaced by 1MHz starting at 2400MHz and ending at 2525MHz. |

##### set\_address(self, address)

|  Name         | `set_address`|
|  -------------| ---------------------------|
|  Parameters   | (list of int) address|
|  Returns      | None|
|  Description  | Set the Crazyradio address. The *address* is 5 bytes long. It should be a list of 5 bytes values.|

##### set\_data\_rate(self, datarate)

 | Name          |`set_datarate`|
 | ------------- |------------------|
 | Parameters    |(int) datarate|
 | Returns       |None|
 | Description   |Set the Crazyradio datarate. *Datarate* is one of `DR_250KPS`, `DR_1MPS` or `DR_2MPS`|

##### set\_power(self, power)

|  Name          |`set_power`|
|  ------------- |----------------------------------------------------------------------------------|
|  Parameters    |(int) power|
|  Returns       |None|
|  Description   |Set the Crazyradio transmit power. *Power* is one of `P_M18DBM`, `P_M12DBM`, `P_M6DBM` or `P_0DBM` respectively for -18dBm, -12dBm, -6dBm and 0dBm.|

##### set\_arc(self, arc)

 | Name         | `set_arc`|
 | -------------| ----------------------------------------------------------------------------------|
 | Parameters   | (int) arc|
 | Returns      | None|
 | Description  | Set the number of retry. 0\<*arc*\<15. See nRF24L01 documentation for more info.|

##### set\_ard\_time(self, us)

|  Name         | `set_ard_time`|
|  -------------| ---------------------------------------------------------------------------------|
|  Parameters   | (int) us|
|  Returns      | None|
|  Description  | Set the time to wait for an Ack in micro seconds. 250\<*us*\<4000. The wait time for an Ack packet corresponds to the time to receive the biggest expected Ack. See nRF24L01 documentation for more info.|

##### set\_ard\_bytes(self, nbytes)

|  Name         | `set_ard_bytes`|
|  -------------| ---------------------------------------------------------------|
|  Parameters   | (int) nbytes|
|  Returns      | None|
|  Description  | Set the time to wait for an Ack in number of ack payload bytes. The Crazyradio will calculate the correct time with the currently selected datarate.|

##### set\_cont\_carrier(self, active)

|  Name         | `set_cont_carrier`|
|  -------------| --------------------------------------------------------|
|  Parameters   | (bool) active|
|  Returns      | None|
|  Description  | Enable or disable the continuous carrier mode. In continuous carrier the Crazyradio transmit a constant sinus at the currently set frequency (channel) and power. This is a test mode that can affect other 2.4GHz devices (ex. wifi) it should only be used in a lab for test purposes.|

##### scan\_channels(self, start, stop, packet)

|  Name         | `scan_channels`|
|  -------------| ----------------------------------|
|  Parameters   | (int) start, (int) stop, (int) packet|
|  Returns      | (list) List of channels that Acked the packet|
|  Description  | Sends \\packet\\ to all channels from start to stop. Returns a list of the channels for which an ACK was received.|

##### send\_packet(self, dataOut)

|  Name         | `send_packet`|
|  -------------| --------------------------------------------------------|
|  Parameters   | (list or tuple) dataOut|
|  Returns      | ([\_radio\_ack](#_radio_ack)) Ack status|
|  Description  | Sends the packet *dataOut* on the configured channel and datarate. Waits for an ack and returns a \_radio\_ack object that contains the ack status and optional ack payload data.|

### \_radio\_ack

#### Fields

|  (bool) ack       | At `True` if an Ack packet has been receive (ie. if the packet was received by the device)|
 | ----------------- |------------------------------------------|
 | (bool) powerDet  | Indicate the nRF24LU1 power detector status. See nRF24LU1 documentation for more information.|
|  (int) retry     |  Number of retry before an ack was received|
|  (tuple) data     | Data payload received in the Ack packet|

#### Methods

None
