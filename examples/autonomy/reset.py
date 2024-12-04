import time

from cflib.utils import uri_helper
from cflib.utils.power_switch import PowerSwitch

uri = uri_helper.uri_from_env(default='radio://0/88/2M/F00D2BEFED')

pwr_switch = PowerSwitch(uri)
pwr_switch.stm_power_cycle()
time.sleep(1)
pwr_switch.close()
