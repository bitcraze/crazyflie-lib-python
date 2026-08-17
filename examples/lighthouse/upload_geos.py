import cflib.crtp  # noqa
from cflib.crazyflie import Crazyflie
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from cflib.localization import LighthouseConfigFileManager
from cflib.localization import LighthouseConfigWriter


# Upload a geometry to one or more Crazyflies.

mgr = LighthouseConfigFileManager()
geos, calibs, type = mgr.read('/path/to/your/geo.yaml')

uri_list = [
    'radio://0/70/2M/E7E7E7E770'
]

# Initialize the low-level drivers
cflib.crtp.init_drivers()

for uri in uri_list:
    with SyncCrazyflie(uri, cf=Crazyflie(rw_cache='./cache')) as scf:
        writer = LighthouseConfigWriter(scf.cf)
        writer.write_and_store_config(data_stored_cb=None, geos=geos, calibs=calibs)
