
"""
This example illustrates how to use CRTP over CPX while also using CPX
to access other targets on the Crazyflie. This is done by connecting to
the Crazyflie and reading out images from the WiFi streamer and naming
them according to the post of the Crazyflie.

For the example to work you will need the WiFi example flashed on the
GAP8 and an up to date code-base on the STM32/ESP32.

"""

import logging
import time
import queue
import threading
import struct

import cflib.crtp
from cflib.crazyflie import Crazyflie
from cflib.crazyflie.log import LogConfig
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from cflib.crazyflie.syncLogger import SyncLogger
from cflib.utils import uri_helper

from cflib.cpx import CPXPacket, CPXFunction, CPXTarget

uri = uri_helper.uri_from_env(default='cpx://aideck-B09D74.local:5000')

# Only output errors from the logging framework
logging.basicConfig(level=logging.ERROR)

class Example(threading.Thread):

  def __init__(self, uri):
      threading.Thread.__init__(self)
      self._lg_stab = LogConfig(name='Stabilizer', period_in_ms=10)
      self._lg_stab.add_variable('stateEstimate.x', 'float')
      self._lg_stab.add_variable('stateEstimate.y', 'float')
      self._lg_stab.add_variable('stateEstimate.z', 'float')      
      self._lg_stab.add_variable('stabilizer.roll', 'float')
      self._lg_stab.add_variable('stabilizer.pitch', 'float')
      self._lg_stab.add_variable('stabilizer.yaw', 'float')

      self._cf = Crazyflie(rw_cache='./cache')
      self._cf.connected.add_callback(self.connected)
      self._cf.disconnected.add_callback(self.disconnected)
      self._cf.open_link(uri)
      self._cpx = None

  def connected(self, uri):
      print("Connected to {}".format(uri))
      self._cpx = self._cf.link.cpx
      self.start()
      try:
          self._cf.log.add_config(self._lg_stab)
          # This callback will receive the data
          self._lg_stab.data_received_cb.add_callback(self._stab_log_data)
          # This callback will be called on errors
          self._lg_stab.error_cb.add_callback(self._stab_log_error)
          # Start the logging
          self._lg_stab.start()
      except KeyError as e:
          print('Could not start log configuration,'
                '{} not found in TOC'.format(str(e)))
      except AttributeError:
          print('Could not add Stabilizer log config, bad configuration.')      

  def disconnected(self, uri):
      print("Disconnected from {}".format(uri))

  def _stab_log_error(self, logconf, msg):
      """Callback from the log API when an error occurs"""
      print('Error when logging %s: %s' % (logconf.name, msg))

  def _stab_log_data(self, timestamp, data, logconf):
      print(f'[{timestamp}][{logconf.name}]: ', end='')
      for name, value in data.items():
          print(f'{name}: {value:3.3f} ', end='')
      print()

  def run(self):
      while True:
          p = self._cpx.receivePacket(CPXFunction.APP)
          [magic, width, height, depth, format, size] = struct.unpack('<BHHBBI', p.data[0:11])
          if (magic == 0xBC):
            print("New image: {}x{}x{}, size is {}b".format(width, height, depth, size))
          

if __name__ == '__main__':
    # Initialize the low-level drivers
    cflib.crtp.init_drivers()

    ex = Example(uri)



    



