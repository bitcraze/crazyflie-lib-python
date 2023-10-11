# Eric Yihan Chen
# The Automatic Coordination of Teams (ACT) Lab
# University of Southern California
# ericyihc@usc.edu
'''
    Simple example that connects to the first Crazyflie found, triggers
    reading of rssi data and acknowledgement rate for every channel (0 to 125).
    It finally sets the Crazyflie channel back to default, plots link
    quality data, and offers good channel suggestion.

    This script should be used on a Crazyflie with bluetooth disabled and RSSI
    ack packet enabled to get RSSI feedback. To configure the Crazyflie in this
    mode build the crazyflie2-nrf-firmware with
    ```make BLE=0 CONFIG=-DRSSI_ACK_PACKET```.
    Additionally, the Crazyflie must be using the default address 0xE7E7E7E7E7.
    See https://github.com/bitcraze/crazyflie-lib-python/issues/131 for more
    informations.
'''
import argparse

import matplotlib.pyplot as plt
import numpy as np

import cflib.drivers.crazyradio as crazyradio

radio = crazyradio.Crazyradio()

# optional user input
parser = argparse.ArgumentParser(description='Key variables')
parser.add_argument(
    '-try', '--try', dest='TRY', type=int, default=100,
    help='the time to send data for each channel'
)
# by default my crazyflie uses channel 80
parser.add_argument(
    '-channel', '--channel', dest='channel', type=int,
    default=80, help='the default channel in crazyflie'
)
# by default my crazyflie uses datarate 2M
parser.add_argument(
    '-rate', '--rate', dest='rate', type=int, default=2,
    help='the default datarate in crazyflie'
)
parser.add_argument(
    '-frac', '--fraction',  dest='fraction', type=float,
    default=0.25, help='top fraction of suggested channels'
)
args = parser.parse_args()

init_channel = args.channel
TRY = args.TRY
Fraction = args.fraction
data_rate = args.rate

radio.set_channel(init_channel)
radio.set_data_rate(data_rate)
SET_RADIO_CHANNEL = 1

rssi_std = []
rssi = []
ack = []
radio.set_arc(0)

for channel in range(0, 126, 1):

    # change Crazyflie channel
    for x in range(50):
        radio.send_packet((0xff, 0x03, SET_RADIO_CHANNEL, channel))

    count = 0
    temp = []

    # change radio channel
    radio.set_channel(channel)

    for i in range(TRY):
        pk = radio.send_packet((0xff, ))
        if pk.ack:
            count += 1
        if pk.ack and len(pk.data) > 2 and \
           pk.data[0] & 0xf3 == 0xf3 and pk.data[1] == 0x01:
            # append rssi data
            temp.append(pk.data[2])

    ack_rate = count / TRY
    if len(temp) > 0:
        rssi_avg = np.mean(temp)
        std = np.std(temp)
    else:
        rssi_avg = np.NaN
        std = np.NaN

    rssi.append(rssi_avg)
    ack.append(ack_rate)
    rssi_std.append(std)

    print('Channel', channel, 'ack_rate:', ack_rate,
          'rssi average:', rssi_avg, 'rssi std:', std)

# change channel back to default
for x in range(50):
    radio.send_packet((0xff, 0x03, SET_RADIO_CHANNEL, init_channel))

# divide each std by 2 for plotting convenience
rssi_std = [x / 2 for x in rssi_std]
rssi_std = np.array(rssi_std)
rssi = np.array(rssi)
ack = np.array(ack)

rssi_rank = []
ack_rank = []

# suggestion for rssi
order = rssi.argsort()
ranks = order.argsort()
for x in range(int(125 * Fraction)):
    for y in range(126):
        if ranks[y] == x:
            rssi_rank.append(y)

# suggestion for ack
order = ack.argsort()
ranks = order.argsort()
for x in range(126, 126 - int(125 * Fraction) - 1, -1):
    for y in range(126):
        if ranks[y] == x:
            ack_rank.append(y)

rssi_set = set(rssi_rank[0:int(125 * Fraction)])
ack_set = set(ack_rank[0:int(125 * Fraction)])
final_rank = rssi_set.intersection(ack_rank)
print('\nSuggested Channels:')
for x in final_rank:
    print('\t', x)

# graph 1 for ack
x = np.arange(0, 126, 1)
fig, ax1 = plt.subplots()
ax1.axis([0, 125, 0, 1.25])
ax1.plot(x, ack, 'b')
ax1.set_xlabel('Channel')
ax1.set_ylabel('Ack Rate', color='b')
for tl in ax1.get_yticklabels():
    tl.set_color('b')

# graph 2 for rssi & rssi_std
ax2 = ax1.twinx()
ax2.grid(True)
ax2.errorbar(x, rssi, yerr=rssi_std, fmt='r-')
ax2.fill_between(x, rssi + rssi_std, rssi - rssi_std,
                 facecolor='orange', edgecolor='k')
ax2.axis([0, 125, 0, 90])
plt.ylabel('RSSI Average', color='r')
for tl in ax2.get_yticklabels():
    tl.set_color('r')
points = np.ones(100)
for x in final_rank:
    ax2.plot((x, x), (0, 100), linestyle='-',
             color='cornflowerblue', linewidth=1)

plt.show()
