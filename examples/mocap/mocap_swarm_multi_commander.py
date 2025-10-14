# -*- coding: utf-8 -*-
#
# ,---------,       ____  _ __
# |  ,-^-,  |      / __ )(_) /_______________ _____  ___
# | (  O  ) |     / __  / / __/ ___/ ___/ __ `/_  / / _ \
# | / ,--'  |    / /_/ / / /_/ /__/ /  / /_/ / / /_/  __/
#    +------`   /_____/_/\__/\___/_/   \__,_/ /___/\___/
#
# Copyright (C) 2025 Bitcraze AB
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, in version 3.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <http://www.gnu.org/licenses/>.
"""
Example of how to connect to a motion capture system and feed positions (only)
to multiple Crazyflies, using the motioncapture library.

The script uses the position high level and the motion commander to fly circles and waypoints.

Set the uri to the radio settings of your Crazyflies, set the rigid body names and
modify the mocap setting matching your system.
"""
import time
from threading import Thread

import motioncapture

import cflib.crtp
from cflib.crazyflie.swarm import CachedCfFactory
from cflib.crazyflie.swarm import Swarm
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from cflib.positioning.motion_commander import MotionCommander
from cflib.positioning.position_hl_commander import PositionHlCommander

# The type of the mocap system
# Valid options are: 'vicon', 'optitrack', 'optitrack_closed_source', 'qualisys', 'nokov', 'vrpn', 'motionanalysis'
mocap_system_type = 'optitrack'

# The host name or ip address of the mocap system
host_name = '10.223.0.31'

# Maps the URIs to the rigid-body names as streamed by, e.g., OptiTrack's Motive
swarm_config = [
    ('radio://0/80/2M/E7E7E7E7E7', 'cf1'),
    #    ('radio://0/80/2M/E7E7E7E7E8', 'cf2'),
    #    ('radio://0/80/2M/E7E7E7E7E9', 'cf3'),
    #   Add more URIs if you want more copters in the swarm
]

uris = [uri for uri, _ in swarm_config]
rbs = {uri: name for uri, name in swarm_config}


class MocapWrapper(Thread):
    def __init__(self, active_rbs_cfs):
        Thread.__init__(self)
        self.active_rbs_cfs = active_rbs_cfs
        self._stay_open = True
        self.counter = 0
        self.start()

    def close(self):
        self._stay_open = False

    def run(self):
        mc = motioncapture.connect(mocap_system_type, {'hostname': host_name})
        while self._stay_open:
            mc.waitForNextFrame()
            self.counter += 1
            for name, obj in mc.rigidBodies.items():
                if name in self.active_rbs_cfs:
                    pos = obj.position
                    # Only send positions
                    self.active_rbs_cfs[name].extpos.send_extpos(pos[0], pos[1], pos[2])
                    if self.counter == 200:
                        print(f'Sent pos {pos} for {name}')
            if self.counter == 200:
                self.counter = 0


def activate_kalman_estimator(scf: SyncCrazyflie):
    scf.cf.param.set_value('stabilizer.estimator', '2')

    # Set the std deviation for the quaternion data pushed into the
    # kalman filter. The default value seems to be a bit too low.
    scf.cf.param.set_value('locSrv.extQuatStdDev', 0.06)


def run_sequence(scf: SyncCrazyflie):
    print('This is: ', scf._link_uri)
    scf.cf.platform.send_arming_request(True)
    time.sleep(1.0)

    # .takeoff() is automatic when entering the "with PositionHlCommander" context
    if rbs[scf._link_uri] == 'cf1':
        with PositionHlCommander(scf, controller=PositionHlCommander.CONTROLLER_PID) as pc:
            pc.set_default_velocity(0.5)
            for i in range(3):  # fly a triangle with changing altitude
                pc.go_to(1.0, 1.0, 1.5)
                pc.go_to(1.0, -1.0, 1.5)
                pc.go_to(0.5, 0.0, 2.0)
            pc.go_to(0.5, 0.0, 0.15)
    elif rbs[scf._link_uri] == 'cf2':
        with PositionHlCommander(scf, controller=PositionHlCommander.CONTROLLER_PID) as pc:
            pc.set_default_velocity(0.3)
            for i in range(3):  # fly side to side
                pc.go_to(0.2, 1.0, 0.85)
                pc.go_to(0.2, -1.0, 0.85)
            pc.go_to(0.0, 0.0, 0.15)
    elif rbs[scf._link_uri] == 'cf3':
        with MotionCommander(scf) as mc:
            # 2 right loops and 2 left loops
            mc.back(0.8)
            time.sleep(1)
            mc.up(0.5)
            time.sleep(1)
            mc.circle_right(0.5, velocity=0.4, angle_degrees=720)
            time.sleep(1)
            mc.up(0.5)
            time.sleep(1)
            mc.circle_left(0.5, velocity=0.4, angle_degrees=720)
            time.sleep(1)
            mc.down(0.5)
    # .land() is automatic when exiting the scope of context "with PositionHlCommander"


if __name__ == '__main__':
    cflib.crtp.init_drivers()

    factory = CachedCfFactory(rw_cache='./cache')
    with Swarm(uris, factory=factory) as swarm:
        active_rbs_cfs = {rbs[uri]: scf.cf for uri, scf in swarm._cfs.items()}
        mocap_thread = MocapWrapper(active_rbs_cfs)

        swarm.parallel_safe(activate_kalman_estimator)
        time.sleep(1)
        swarm.reset_estimators()
        time.sleep(2)
        swarm.parallel_safe(run_sequence)

    mocap_thread.close()
