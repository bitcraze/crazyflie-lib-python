import time
from threading import Thread, Lock

import motioncapture

import cflib.crtp
from cflib.crazyflie.swarm import CachedCfFactory
from cflib.crazyflie.swarm import Swarm
from cflib.crazyflie import Crazyflie
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from cflib.utils.reset_estimator import reset_estimator
from cflib.positioning.position_hl_commander import PositionHlCommander
from cflib.positioning.motion_commander import MotionCommander

# The type of the mocap system
# Valid options are: 'vicon', 'optitrack', 'optitrack_closed_source', 'qualisys', 'nokov', 'vrpn', 'motionanalysis'
mocap_system_type = 'optitrack'

# The host name or ip address of the mocap system
host_name = '192.168.5.21'

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
                        print(f"Sent pos {pos} for {name}")
            if self.counter == 200:
                self.counter = 0

def run_sequence(scf):
    print("This is: ", scf._link_uri)
    scf.cf.platform.send_arming_request(True)
    time.sleep(1.0)

    ################################################################################
    # .takeoff() is automatic when entering the "with PositionHlCommander" context #
    ################################################################################
    if scf._link_uri == 'radio://0/80/2M/E7E7E7E7E7':
        with PositionHlCommander(scf, controller=PositionHlCommander.CONTROLLER_PID) as pc:
            pc.set_default_velocity(0.5)
            #################################################################################
            # 6 repetitions, at .5 speed, take ~1':15 and drop the battery from 4.2 to 3.9V #
            #################################################################################
            for i in range(6): # fly a triangle with changing altitude
                pc.go_to(1.0, 1.0, 1.5)
                pc.go_to(1.0, -1.0, 1.5)
                pc.go_to(0.5, 0.0, 2.0)
            pc.go_to(0.5, 0.0, 0.15)
    elif scf._link_uri == 'radio://0/90/2M/E7E7E7E7E8':
        with PositionHlCommander(scf, controller=PositionHlCommander.CONTROLLER_PID) as pc:
            pc.set_default_velocity(0.3)
            ######################
            # Scripted behaviour #
            ######################
            for i in range(6): # fly side to side
                pc.go_to(0.2, 1.0, 0.85)
                pc.go_to(0.2, -1.0, 0.85)
            pc.go_to(0.0, 0.0, 0.15)
    elif scf._link_uri == 'radio://0/100/2M/E7E7E7E7E9':
        with MotionCommander(scf) as mc:
            #################################################################################
            # 3 right loops and 3 left loops take ~1' and drop the battery from 4.2 to 4.0V #
            #################################################################################
            mc.back(0.8)
            time.sleep(1)
            mc.up(0.5)
            time.sleep(1)
            mc.circle_right(0.5, velocity=0.4, angle_degrees=1080)
            time.sleep(1)
            mc.up(0.5)
            time.sleep(1)
            mc.circle_left(0.5, velocity=0.4, angle_degrees=1080)
            time.sleep(1)
            mc.down(0.5)
    #####################################################################################
    # .land() is automatic when exiting the scope of context "with PositionHlCommander" #
    #####################################################################################

if __name__ == '__main__':
    cflib.crtp.init_drivers()

    # Uncomment the URIs to connect to
    uris = [
            'radio://0/80/2M/E7E7E7E7E7',
            # 'radio://0/90/2M/E7E7E7E7E8',
            # 'radio://0/100/2M/E7E7E7E7E9',
        ]

    # Maps the URIs to the rigid-body names as streamed by, e.g., OptiTrack's Motive
    rbs = {
            'radio://0/80/2M/E7E7E7E7E7' : 'E7',
            'radio://0/90/2M/E7E7E7E7E8' : 'E8',
            'radio://0/100/2M/E7E7E7E7E9' : 'E9'
        }

    
    factory = CachedCfFactory(rw_cache='./cache')
    with Swarm(uris, factory=factory) as swarm:
        active_rbs_cfs = {rbs[uri]: scf.cf for uri, scf in swarm._cfs.items()}
        mocap_thred = MocapWrapper(active_rbs_cfs)

        swarm.reset_estimators()
        time.sleep(2)
        swarm.parallel_safe(run_sequence)

    mocap_thred.close()
