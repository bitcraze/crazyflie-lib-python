import yaml

first_config = ''  # Add the old config
second_config = ''  # Add the new config

x1 = []
y1 = []
z1 = []
bs_id1 = []

x2 = []
y2 = []
z2 = []
bs_id2 = []

difx = []
dify = []
difz = []

with open(first_config, 'r') as f:
    data1 = yaml.load(f, Loader=yaml.SafeLoader)
print('First configuration:')
for i in range(len(data1['geos'].keys())):
    bs_id1.append(i+1)
    x1.append(data1['geos'][i]['origin'][0])
    y1.append(data1['geos'][i]['origin'][1])
    z1.append(data1['geos'][i]['origin'][2])
    print(f'Base station: {bs_id1[i]}, position: {x1[i], y1[i], z1[i]}')

with open(second_config, 'r') as f:
    data2 = yaml.load(f, Loader=yaml.SafeLoader)

print('\n Second configuration:')
for i in range(len(data2['geos'].keys())):
    bs_id2.append(i+1)
    x2.append(data2['geos'][i]['origin'][0])
    y2.append(data2['geos'][i]['origin'][1])
    z2.append(data2['geos'][i]['origin'][2])
    print(f'Base station: {bs_id2[i]}, position: {x2[i], y2[i], z2[i]}')

print('')
for i in range(len(bs_id1)):
    difx.append(x1[i] - x2[i])
    dify.append(y1[i] - y2[i])
    difz.append(z1[i] - z2[i])
    print(f'Base station {i+1} moved by {difz[i]} on x, {difz[i]} on y, {difz[i]} on z.')
