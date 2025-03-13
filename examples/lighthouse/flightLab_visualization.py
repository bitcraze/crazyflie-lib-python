import matplotlib.pyplot as plt
import yaml
import numpy as np

x = []
y = []
z = []
bs_id = []
with open('Geo_Estimation_Files/Lighthouse_x16.yaml', 'r') as f:

    data = yaml.load(f, Loader=yaml.SafeLoader)
# Print the values as a dictionary
# print(data['geos'])
for i in range(len(data['geos'].keys())):
    bs_id.append(i+1)
    x.append(data['geos'][i]['origin'][0])
    y.append(data['geos'][i]['origin'][1])
    z.append(data['geos'][i]['origin'][2])
    print(f'Base station: {bs_id[i]}, position: {x[i], y[i], z[i]}')


font1 = {'family': 'serif', 'color': '#2d867e', 'size': 20}
font2 = {'family': 'serif', 'color': '#2d867e', 'size': 15}

fig = plt.figure()
ax = fig.add_subplot(1, 2, 1, projection='3d')

# ax.scatter(x, y, z, color='black')

for j in range(len(x)):
    ax.scatter(x[j], y[j], z[j], color='black')
    ax.text(x[j], y[j], z[j], bs_id[j])


x1, z1 = np.meshgrid([-4.6, 4.6], [0, 3.65])
y1 = np.full(shape=(2, 2), fill_value=3.6)
y4 = np.full(shape=(2, 2), fill_value=-16)

y2, z2 = np.meshgrid([3.6, -16], [0, 3.65])
x2 = np.full(shape=(2, 2), fill_value=-4.6)
x3 = np.full(shape=(2, 2), fill_value=4.6)

ax.plot_surface(x1, y1, z1, color='blue', alpha=.1)
ax.plot_surface(x2, y2, z2, color='blue', alpha=.1)
ax.plot_surface(x3, y2, z2, color='blue', alpha=.1)
ax.plot_surface(x1, y4, z1, color='blue', alpha=.1)


ax.set_xlabel('X-axis')
ax.set_ylabel('Y-axis')
ax.set_zlabel('Z-axis')
ax.set_aspect('equal')
ax.set_zlim(0, 4)

ax = fig.add_subplot(1, 2, 2)

for j in range(len(x)):
    ax.scatter(x[j], y[j], color='black')
    ax.text(x[j], y[j], bs_id[j])

ax.set_xlabel('X-axis')
ax.set_ylabel('Y-axis')
ax.set_aspect('equal')
ax.grid()

plt.show(block=False)
plt.pause(1)
input()
plt.close
