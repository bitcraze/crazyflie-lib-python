#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#     ||          ____  _ __
#  +------+      / __ )(_) /_______________ _____  ___
#  | 0xBC |     / __  / / __/ ___/ ___/ __ `/_  / / _ \
#  +------+    / /_/ / / /_/ /__/ /  / /_/ / / /_/  __/
#   ||  ||    /_____/_/\__/\___/_/   \__,_/ /___/\___/
#
#  Copyright (C) 2011-2013 Bitcraze AB
#
#  Crazyflie Nano Quadcopter Client
#
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License
#  as published by the Free Software Foundation; either version 2
#  of the License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#  You should have received a copy of the GNU General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA  02110-1301, USA.
"""
Gui une the PID controller of the crazyflie

"""
import logging
import sys
import time

import matplotlib.pyplot as plt
import tkinter as tk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

import cflib.crtp
from cflib.crazyflie import Crazyflie
from cflib.crazyflie.log import LogConfig
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from cflib.crazyflie.syncLogger import SyncLogger

URI = 'radio://0/30/2M/E7E7E7E702'
STANDARD_HEIGHT = 0.8
STEP_RESPONSE_TIME = 3.0
STEP_SIZE = -0.2  # meters

if len(sys.argv) > 1:
    URI = sys.argv[1]
elif len(sys.argv) > 2:
    STANDARD_HEIGHT = sys.argv[2]

# Only output errors from the logging framework
logging.basicConfig(level=logging.ERROR)


class TunerGUI:
    def __init__(self, master):
        self.master = master
        self.master.title('PID tuner Crazyflie')

        self.figplot = plt.Figure(figsize=(5, 4), dpi=100)
        self.ax2 = self.figplot.add_subplot(111)
        self.line2 = FigureCanvasTkAgg(self.figplot, self.master)
        self.line2.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)

        self.scale_Kp = tk.Scale(master, label='scale_Kp', from_=0, to=100,
                                 length=1200, tickinterval=5, resolution=0.1,
                                 orient=tk.HORIZONTAL)
        self.scale_Ki = tk.Scale(master, label='scale_Ki', from_=0, to=50,
                                 length=1200, tickinterval=3, resolution=0.1,
                                 orient=tk.HORIZONTAL)
        self.scale_Kd = tk.Scale(master, label='scale_Kd', from_=0, to=50,
                                 length=1200, tickinterval=3, resolution=0.1,
                                 orient=tk.HORIZONTAL)
        self.scale_vMax = tk.Scale(master, label='vMax', from_=0, to=5,
                                   length=1200, tickinterval=5, resolution=0.1,
                                   orient=tk.HORIZONTAL)

        self.scale_Kp.pack()
        self.scale_Ki.pack()
        self.scale_Kd.pack()
        self.scale_vMax.pack()

        self.pos_array_prev = []
        self.sp_array_prev = []
        self.time_array_prev = []

    def draw_plot(self, time_array, pos_array, sp_array):

        self.ax2.clear()
        self.ax2.plot(self.time_array_prev, self.pos_array_prev,
                      label='pos_z', color='red', alpha=0.5)

        self.ax2.plot(time_array, pos_array, label='pos', color='red')
        self.ax2.plot(time_array, sp_array, label='sp', color='blue')
        self.line2.draw()
        self.pos_array_prev = pos_array
        self.sp_array_prev = sp_array
        self.time_array_prev = time_array

    def clear_plot(self):
        self.ax2.clear()
        self.line2.draw()
        self.time_array_prev = []
        self.pos_array_prev = []
        self.sp_array_prev = []


class TunerControlCF:
    def __init__(self, pid_gui, scf):
        self.cf = scf
        self.pid_gui = pid_gui

        self.label = tk.Label(self.pid_gui.master, text='Choose an axis!')
        self.label.pack()
        variable = tk.StringVar(self.pid_gui.master)
        variable.set('z')
        self.dropdown = tk.OptionMenu(
            self.pid_gui.master, variable, 'x', 'y', 'z',
            command=self.change_param_axis_callback)
        self.dropdown.pack()
        self.axis_choice = 'z'

        self.label = tk.Label(self.pid_gui.master,
                              text='Choose velocity or position!')
        self.label.pack()
        variable_pos = tk.StringVar(self.pid_gui.master)
        variable_pos.set('pos')
        self.dropdown = tk.OptionMenu(
            self.pid_gui.master, variable_pos, 'pos', 'vel',
            command=self.change_param_unit_callback)
        self.dropdown.pack()
        self.unit_choice = 'pos'

        self.button_send = tk.Button(
            self.pid_gui.master, text='SEND PID GAINS',
            command=self.send_pid_gains).pack()
        self.button_step = tk.Button(
            self.pid_gui.master, text='DO STEP',
            command=self.do_step).pack()
        self.button_quit = tk.Button(
            self.pid_gui.master, text='STOP',
            command=self.stop_gui).pack()

        self.cf.param.add_update_callback(
            group='posCtlPid', name='zKp', cb=self.param_updated_callback_Kp)
        self.cf.param.add_update_callback(
            group='posCtlPid', name='zKi', cb=self.param_updated_callback_Ki)
        self.cf.param.add_update_callback(
            group='posCtlPid', name='zKd', cb=self.param_updated_callback_Kd)
        self.cf.param.add_update_callback(
            group='posCtlPid', name='xyVelMax',
            cb=self.param_updated_callback_vMax)

        self.current_value_kp = 0
        self.current_value_kd = 0
        self.current_value_ki = 0
        self.current_value_vmax = 0

        self.cf.param.request_param_update('posCtlPid.zKp')
        self.cf.param.request_param_update('posCtlPid.zKi')
        self.cf.param.request_param_update('posCtlPid.zKd')
        self.cf.param.request_param_update('posCtlPid.xyVelMax')

        time.sleep(0.1)

        self.update_scale_info()

        self.commander = cf.high_level_commander
        self.cf.param.set_value('commander.enHighLevel', '1')
        self.take_off(STANDARD_HEIGHT)

    def update_scale_info(self):
        print('update info')
        self.pid_gui.scale_Kp.set(self.current_value_kp)
        self.pid_gui.scale_Kd.set(self.current_value_kd)
        self.pid_gui.scale_Ki.set(self.current_value_ki)
        self.pid_gui.scale_vMax.set(self.current_value_vmax)

    # Buttons

    def send_pid_gains(self):
        print('Sending to the ' + self.axis_choice +
              'position PID controller: Kp: ' +
              str(self.pid_gui.scale_Kp.get()) +
              ', Ki: ' + str(self.pid_gui.scale_Ki.get()) +
              ', Kd: '+str(self.pid_gui.scale_Ki.get()))
        cf.param.set_value(self.unit_choice+'CtlPid.'+self.axis_choice +
                           'Kp', self.pid_gui.scale_Kp.get())
        cf.param.set_value(self.unit_choice+'CtlPid.'+self.axis_choice +
                           'Ki', self.pid_gui.scale_Ki.get())
        cf.param.set_value(self.unit_choice+'CtlPid.'+self.axis_choice +
                           'Kd', self.pid_gui.scale_Kd.get())
        cf.param.set_value('posCtlPid.xyVelMax', self.pid_gui.scale_vMax.get())

        time.sleep(0.1)

        self.update_scale_info()

    def do_step(self):
        print('do step')
        log_config = LogConfig(name='Position setpoint', period_in_ms=10)
        log_config.add_variable('stateEstimate.' + self.axis_choice, 'float')
        log_config.add_variable('ctrltarget.' + self.axis_choice, 'float')

        if self.axis_choice == 'z':
            self.commander.go_to(0, 0, STEP_SIZE, 0, 0.6, relative=True)
        elif self.axis_choice == 'x':
            self.commander.go_to(STEP_SIZE, 0, 0, 0, 0.6, relative=True)
        elif self.axis_choice == 'y':
            self.commander.go_to(0, STEP_SIZE, 0, 0, 0.6, relative=True)
        else:
            print('WRONG CHOICE?!?!')
            self.stop_gui()

        current_time = time.time()

        pos_history = []
        sp_history = []
        time_history = []
        with SyncLogger(self.cf, log_config) as logger:
            for log_entry in logger:
                data = log_entry[1]

                pos_history.append(data['stateEstimate.' + self.axis_choice])
                sp_history.append(data['ctrltarget.' + self.axis_choice])
                time_history.append(time.time() - current_time)

                if ((time.time() - current_time) > STEP_RESPONSE_TIME):
                    break
        # print(pos_history)
        # print(sp_history)
        self.pid_gui.draw_plot(time_history, pos_history, sp_history)
        if self.axis_choice == 'z':
            self.commander.go_to(0, 0, -1*STEP_SIZE, 0, 1.0, relative=True)
        elif self.axis_choice == 'x':
            self.commander.go_to(-1*STEP_SIZE, 0, 0, 0, 1.0, relative=True)
        elif self.axis_choice == 'y':
            self.commander.go_to(0, -1*STEP_SIZE, 0, 0, 1.0, relative=True)
        else:
            print('WRONG CHOICE?!?!')
            self.stop_gui()

    def stop_gui(self):
        self.pid_gui.master.quit()
        self.land_and_stop()

    # parameter update
    def change_param_axis_callback(self, value_axis):
        #
        print(self.unit_choice + 'CtlPid.'+value_axis)

        groupname = self.unit_choice + 'CtlPid'
        self.cf.param.remove_update_callback(
            group=groupname, name=self.axis_choice + 'Kp')
        self.cf.param.remove_update_callback(
            group=groupname, name=self.axis_choice + 'Ki')
        self.cf.param.remove_update_callback(
            group=groupname, name=self.axis_choice + 'Kd')

        time.sleep(0.1)
        self.cf.param.add_update_callback(
            group=groupname, name=value_axis +
            'Kp', cb=self.param_updated_callback_Kp)
        self.cf.param.add_update_callback(
            group=groupname, name=value_axis +
            'Ki', cb=self.param_updated_callback_Ki)
        self.cf.param.add_update_callback(
            group=groupname, name=value_axis +
            'Kd', cb=self.param_updated_callback_Kd)

        self.cf.param.request_param_update(groupname+'.'+value_axis+'Kp')
        self.cf.param.request_param_update(groupname+'.'+value_axis+'Ki')
        self.cf.param.request_param_update(groupname+'.'+value_axis+'Kd')
        time.sleep(0.1)

        self.update_scale_info()
        self.pid_gui.clear_plot()
        self.axis_choice = value_axis

    # parameter update
    def change_param_unit_callback(self, value_unit):
        #
        print(value_unit + 'CtlPid.' + self.axis_choice)

        groupname_old = self.unit_choice + 'CtlPid'
        self.cf.param.remove_update_callback(
            group=groupname_old, name=self.axis_choice + 'Kp')
        self.cf.param.remove_update_callback(
            group=groupname_old, name=self.axis_choice + 'Ki')
        self.cf.param.remove_update_callback(
            group=groupname_old, name=self.axis_choice + 'Kd')

        time.sleep(0.1)
        groupname_new = value_unit + 'CtlPid'
        self.cf.param.add_update_callback(
            group=groupname_new, name=self.axis_choice +
            'Kp', cb=self.param_updated_callback_Kp)
        self.cf.param.add_update_callback(
            group=groupname_new, name=self.axis_choice +
            'Ki', cb=self.param_updated_callback_Ki)
        self.cf.param.add_update_callback(
            group=groupname_new, name=self.axis_choice +
            'Kd', cb=self.param_updated_callback_Kd)

        print(groupname_new+'.'+self.axis_choice+'Kp')
        self.cf.param.request_param_update(
            groupname_new+'.'+self.axis_choice+'Kp')
        self.cf.param.request_param_update(
            groupname_new+'.'+self.axis_choice+'Ki')
        self.cf.param.request_param_update(
            groupname_new+'.'+self.axis_choice+'Kd')
        time.sleep(0.1)

        self.update_scale_info()

        self.unit_choice = value_unit

    def param_updated_callback_Kp(self, name, value):
        self.current_value_kp = float(value)

    def param_updated_callback_Ki(self, name, value):
        self.current_value_ki = float(value)

    def param_updated_callback_Kd(self, name, value):
        self.current_value_kd = float(value)

    def param_updated_callback_vMax(self, name, value):
        self.current_value_vmax = float(value)

    def take_off(self, height):
        self.commander.takeoff(height, 2.0)

    def land_and_stop(self):
        self.commander.land(0.0, 2.0)
        time.sleep(2)
        self.commander.stop()


def wait_for_position_estimator(scf):
    print('Waiting for estimator to find position...')

    log_config = LogConfig(name='Kalman Variance', period_in_ms=500)
    log_config.add_variable('kalman.varPX', 'float')
    log_config.add_variable('kalman.varPY', 'float')
    log_config.add_variable('kalman.varPZ', 'float')

    var_y_history = [1000] * 10
    var_x_history = [1000] * 10
    var_z_history = [1000] * 10

    threshold = 0.001

    with SyncLogger(scf, log_config) as logger:
        for log_entry in logger:
            data = log_entry[1]

            var_x_history.append(data['kalman.varPX'])
            var_x_history.pop(0)
            var_y_history.append(data['kalman.varPY'])
            var_y_history.pop(0)
            var_z_history.append(data['kalman.varPZ'])
            var_z_history.pop(0)

            min_x = min(var_x_history)
            max_x = max(var_x_history)
            min_y = min(var_y_history)
            max_y = max(var_y_history)
            min_z = min(var_z_history)
            max_z = max(var_z_history)

            # print("{} {} {}".
            #       format(max_x - min_x, max_y - min_y, max_z - min_z))

            if (max_x - min_x) < threshold and (
                    max_y - min_y) < threshold and (
                    max_z - min_z) < threshold:
                break


if __name__ == '__main__':

    root = tk.Tk()
    pid_gui = TunerGUI(root)

    cflib.crtp.init_drivers(enable_debug_driver=False)
    cf = Crazyflie(rw_cache='./cache')
    with SyncCrazyflie(URI, cf) as scf:
        wait_for_position_estimator(scf)
        cf_ctrl = TunerControlCF(pid_gui, cf)
        tk.mainloop()
