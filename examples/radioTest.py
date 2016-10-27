import numpy as np
import matplotlib.pyplot as plt
import statistics
import cflib.drivers.crazyradio as crazyradio

radio = crazyradio.Crazyradio()
#by default my crazyflie uses channel 80

radio.set_channel(80)
radio.set_data_rate(2)

TRY = 100
SET_RADIO_CHANNEL = 1
Fraction = 0.25
rssi_std = []
rssi = []
ack = []
channel = 0

#initialize channel
for x in range(20):
	radio.send_packet((0xff, 0xf3, SET_RADIO_CHANNEL, 0))

while(channel < 126):
	count = 0
	rssi_sum = 0
	temp = []
	radio.set_arc(0)
	
	for i in range(TRY):
		pk = radio.send_packet((0xff, ))
		if pk.ack:
			count += 1
		if pk.ack and len(pk.data) > 2 and pk.data[0] & 0xf3 == 0xf3 and pk.data[1] == 0x01:
			rssi_sum += pk.data[2]
			temp.append(pk.data[2])
			
	ack_rate = count / TRY
	rssi_avg = rssi_sum / count
	std = statistics.stdev(temp)

	rssi.append(rssi_avg)
	ack.append(ack_rate)
	rssi_std.append(std)
	
	print("Channel", channel, "ack_rate:", ack_rate, "rssi average:", rssi_avg, "rssi std:", std)
	channel += 1
	for x in range(20):
		radio.send_packet((0xff, 0xf3, SET_RADIO_CHANNEL, channel))

#store data
fh = open("data.txt", "w")

for x in range(126):
	fh.write(str(rssi_std[x]) + "\n")
for x in range(126):
	fh.write(str(rssi[x]) + "\n")
for x in range(126):
	fh.write(str(ack[x]) + "\n")
fh.close()

#divide each std by 2 for plotting convenience
for x in range(126):
        rssi_std[x] /= 2

rssi_std = np.array(rssi_std)
rssi = np.array(rssi)
ack = np.array(ack)

rssi_rank = []
ack_rank = []

#suggestion for rssi
order = rssi.argsort()
ranks = order.argsort()
for x in range(int(125*Fraction)):
	for y in range(126):
		if ranks[y] == x:
			rssi_rank.append(y)

#suggestion for ack
order = ack.argsort()
ranks = order.argsort()
for x in range(126, 126-int(125*Fraction)-1, -1):
	for y in range(126):
		if ranks[y] == x:
			ack_rank.append(y)
			
#print("\nSuggested Channels:\nRSSI low 25%: \t Ack high 25%: \tRank:" )
#for x in range(int(125*Fraction)):
#	print(rssi_rank[x], "\t\t ", ack_rank[x], "\t\t", x)

rssi_set = set()
ack_set = set()
for x in range(int(125*Fraction)):
	rssi_set.add(rssi_rank[x])
	ack_set.add(ack_rank[x])

final_rank = rssi_set.intersection(ack_rank)
print("\nSuggested Channels:")
for x in final_rank:
	print("\t", x)

#graph 1 for ack
x = np.arange(0, 126, 1)
fig, ax1 = plt.subplots()
ax1.axis([0, 125, 0, 1.25])
ax1.plot(x, ack, 'b')
ax1.set_xlabel('Channel')
ax1.set_ylabel('Ack Rate', color = 'b')
for tl in ax1.get_yticklabels():
    tl.set_color('b')

#graph 2 for rssi & rssi_std
ax2 = ax1.twinx()
ax2.grid(True)
ax2.errorbar(x, rssi, yerr=rssi_std, fmt='r-')
ax2.fill_between(x, rssi+rssi_std, rssi-rssi_std, facecolor='orange' ,edgecolor='k')
ax2.axis([0, 125, 0, 90])
plt.ylabel('RSSI Average', color = 'r')
for tl in ax2.get_yticklabels():
    tl.set_color('r')
points = np.ones(100)
for x in final_rank:
	ax2.plot((x,x), (0,100), linestyle='-', color='cornflowerblue', linewidth=1)

plt.show()