#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
#     ||          ____  _ __
#  +------+      / __ )(_) /_______________ _____  ___
#  | 0xBC |     / __  / / __/ ___/ ___/ __ `/_  / / _ \
#  +------+    / /_/ / / /_/ /__/ /  / /_/ / / /_/  __/
#   ||  ||    /_____/_/\__/\___/_/   \__,_/ /___/\___/
#
#  Copyright (C) 2018-2022 Bitcraze AB
#
#  Crazyflie Python Library
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
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
"""
Example script which can be used to fly the Crazyflie in "FPV" mode
using the Flow deck and the AI deck.

The example shows how to connect to a Crazyflie over the WiFi and
use both CPX and CRTP for communication over WiFI.

When the application is started the Crazyflie will hover at 0.3 m. The
Crazyflie can then be controlled by using keyboard input:
 * Move by using the arrow keys (left/right/forward/backwards)
 * Adjust the right with w/s (0.1 m for each keypress)
 * Yaw slowly using a/d (CCW/CW)
 * Yaw fast using z/x (CCW/CW)

The demo is ended by closing the application.

For the example to run the following hardware is needed:
 * Crazyflie 2.1
 * Crazyradio PA
 * Flow v2 deck
 * AI deck 1.1
"""
import logging
import struct
import sys
import threading

import numpy as np

import cflib.crtp
from cflib.cpx import CPXFunction
from cflib.crazyflie import Crazyflie
from cflib.crazyflie.log import LogConfig
from cflib.utils import uri_helper

try:
    from sip import setapi
    setapi('QVariant', 2)
    setapi('QString', 2)
except ImportError:
    pass

from PyQt6 import QtCore, QtWidgets, QtGui

logging.basicConfig(level=logging.INFO)

URI = uri_helper.uri_from_env(default='usb://0')


# Set the speed factor for moving and rotating
SPEED_FACTOR = 0.3

if len(sys.argv) > 1:
    URI = sys.argv[1]


class MainWindow(QtWidgets.QWidget):

    def __init__(self, URI):
        QtWidgets.QWidget.__init__(self)

        self.setWindowTitle('Estimator stuff')

        self.mainLayout = QtWidgets.QVBoxLayout()
        self.gridLayout = QtWidgets.QGridLayout()

        label_stdflow = QtWidgets.QLabel('std_flow')
        label_stdflow.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)
        self.gridLayout.addWidget(label_stdflow, 0, 0, 1, 1)

        self.stdflowvalueslider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        self.stdflowvalueslider.setMinimum(1)  # 0.1 * 10
        self.stdflowvalueslider.setMaximum(100)  # 10.0 * 10
        self.stdflowvalueslider.setSingleStep(1)  # 0.1 * 10
        self.stdflowvalue = QtWidgets.QLabel("0")
        layoutstdflow = QtWidgets.QVBoxLayout()
        layoutstdflow.addWidget(self.stdflowvalueslider)
        layoutstdflow.addWidget(self.stdflowvalue)
        self.gridLayout.addLayout(layoutstdflow, 0, 1, 1, 1)


        label_stdLH= QtWidgets.QLabel('std_LH')
        label_stdLH.setAlignment(QtCore.Qt.AlignmentFlag.AlignLeft)
        self.gridLayout.addWidget(label_stdLH, 1, 0, 1, 1)

        resolution_lighthouse = 0.0001
        self.stdLHvalueslider = QtWidgets.QSlider(QtCore.Qt.Orientation.Horizontal)
        self.stdLHvalueslider.setMinimum(1)  # 0.0001 / 0.0001
        self.stdLHvalueslider.setMaximum(100)  # 0.0100 / 0.0001
        self.stdLHvalueslider.setSingleStep(1)  #0.0001 / 0.0001
        self.stdLHvalue = QtWidgets.QLabel("0.000")
        layoutstdLH = QtWidgets.QVBoxLayout()
        layoutstdLH.addWidget(self.stdLHvalueslider)
        layoutstdLH.addWidget(self.stdLHvalue)
        self.gridLayout.addLayout(layoutstdLH, 1, 1, 1, 1)


        self.mainLayout.addLayout(self.gridLayout)

        self.gridLayout2 = QtWidgets.QGridLayout()
        label_empty = QtWidgets.QLabel(' ')
        label_x_txt = QtWidgets.QLabel('x')
        label_y_txt = QtWidgets.QLabel('y')
        label_z_txt = QtWidgets.QLabel('z')
        label_pos_txt = QtWidgets.QLabel('Pos')
        label_vel_txt = QtWidgets.QLabel('Vel')
        label_x_est_txt = QtWidgets.QLabel('0.0')
        label_y_est_txt = QtWidgets.QLabel('0.0')
        label_z_est_txt = QtWidgets.QLabel('0.0')
        label_Pz_est_txt = QtWidgets.QLabel('0.0')
        label_Py_est_txt = QtWidgets.QLabel('0.0')
        label_Px_est_txt = QtWidgets.QLabel('0.0')
        label_varx_txt = QtWidgets.QLabel('0.0')
        label_vary_txt = QtWidgets.QLabel('0.0')
        label_varz_txt = QtWidgets.QLabel('0.0')
        label_varPx_txt = QtWidgets.QLabel('0.0')
        label_varPy_txt = QtWidgets.QLabel('0.0')
        label_varPz_txt = QtWidgets.QLabel('0.0')



        self.gridLayout2.addWidget(label_x_txt, 0,1,1,1)
        self.gridLayout2.addWidget(label_y_txt, 0,2,1,1)
        self.gridLayout2.addWidget(label_z_txt, 0,3,1,1)
        self.gridLayout2.addWidget(label_pos_txt, 1, 0, 1, 1)
        self.gridLayout2.addWidget(label_x_est_txt, 1, 1, 1, 1)
        self.gridLayout2.addWidget(label_y_est_txt, 1, 2, 1, 1)
        self.gridLayout2.addWidget(label_z_est_txt, 1, 3, 1, 1)
        self.gridLayout2.addWidget(label_varx_txt, 2, 1, 1, 1)
        self.gridLayout2.addWidget(label_vary_txt, 2, 2, 1, 1)
        self.gridLayout2.addWidget(label_varz_txt, 2, 3, 1, 1)
        self.gridLayout2.addWidget(label_vel_txt, 3, 0, 1, 1)
        self.gridLayout2.addWidget(label_Px_est_txt, 3, 1, 1, 1)
        self.gridLayout2.addWidget(label_Py_est_txt, 3, 2, 1, 1)
        self.gridLayout2.addWidget(label_Pz_est_txt, 3, 3, 1, 1)
        self.gridLayout2.addWidget(label_varPx_txt, 4, 1, 1, 1)
        self.gridLayout2.addWidget(label_varPy_txt, 4, 2, 1, 1)
        self.gridLayout2.addWidget(label_varPz_txt, 4, 3, 1, 1)
        self.mainLayout.addLayout(self.gridLayout2)


        self.setLayout(self.mainLayout)
        self.stdflowvalueslider.sliderReleased.connect(self.on_value_changed_flow)
        self.stdLHvalueslider.sliderReleased.connect(self.on_value_changed_LH)

        cflib.crtp.init_drivers()
        self.cf = Crazyflie(ro_cache=None, rw_cache='cache')

        # Connect callbacks from the Crazyflie API
        self.cf.connected.add_callback(self.connected)
        self.cf.disconnected.add_callback(self.disconnected)

        # Connect to the Crazyflie
        self.cf.open_link(URI)
        self.cf.param.add_update_callback(group='motion', name='flowStdFixed',
                                 cb=self.param_motion_std_callback)
        self.cf.param.add_update_callback(group='lighthouse', name='sweepStd2',
                                 cb=self.param_lighthouse_std_callback)
        if not self.cf.link:
            print('Could not connect to Crazyflie')
            sys.exit(1)

        # get current value of motion.flowStdFixed from crazyflie

        '''self.hover = {'x': 0.0, 'y': 0.0, 'z': 0.0, 'yaw': 0.0, 'height': 0.3}

        self.hoverTimer = QtCore.QTimer()
        self.hoverTimer.timeout.connect(self.sendHoverCommand)
        self.hoverTimer.setInterval(100)
        self.hoverTimer.start()'''

    def param_motion_std_callback(self, name, value):
        # print value and set slider back to this value
        print("param callback: " + name + " " + "{:.1f}".format(float(value)))
        self.stdflowvalueslider.setValue(int(float(value)*10))
        value_str = "{:.1f}".format(float(value))
        self.stdflowvalue.setText(value_str)

    def param_lighthouse_std_callback(self, name, value):
        # print value and set slider back to this value
        print("param callback: " + name + " " + "{:.4f}".format(float(value)))
        self.stdLHvalueslider.setValue(int(float(value)*10000))
        value_str = "{:.4f}".format(float(value))
        self.stdLHvalue.setText(value_str)

    def on_value_changed_flow(self):
        value = self.stdflowvalueslider.value()
        value_str = "{:.1f}".format(value*0.1)
        self.stdflowvalue.setText(value_str)
        self.cf.param.set_value('motion.flowStdFixed', value_str)
        print("send new flow std dev to crazyflie: " + value_str)

    def on_value_changed_LH(self):
        value = self.stdLHvalueslider.value()
        value_str = "{:.4f}".format(value*0.0001)
        self.stdLHvalue.setText(value_str)
        self.cf.param.set_value('lighthouse.sweepStd2', value_str)
        print("send new LH std dev to crazyflie: " + value_str)

    def log_var_callback(self, timestamp, data, logconf):
        self.gridLayout2.itemAtPosition(2,1).widget().setText("{:.5f}".format(data['kalman.varX']))
        self.gridLayout2.itemAtPosition(2,2).widget().setText("{:.5f}".format(data['kalman.varY']))
        self.gridLayout2.itemAtPosition(2,3).widget().setText("{:.5f}".format(data['kalman.varZ']))
        self.gridLayout2.itemAtPosition(4,1).widget().setText("{:.5f}".format(data['kalman.varPX']))
        self.gridLayout2.itemAtPosition(4,2).widget().setText("{:.5f}".format(data['kalman.varPY']))
        self.gridLayout2.itemAtPosition(4,3).widget().setText("{:.5f}".format(data['kalman.varPZ']))

    def log_est_callback(self, timestamp, data, logconf):
        self.gridLayout2.itemAtPosition(1,1).widget().setText("{:.5f}".format(data['kalman.stateX']))
        self.gridLayout2.itemAtPosition(1,2).widget().setText("{:.5f}".format(data['kalman.stateY']))
        self.gridLayout2.itemAtPosition(1,3).widget().setText("{:.5f}".format(data['kalman.stateZ']))
        self.gridLayout2.itemAtPosition(3,1).widget().setText("{:.5f}".format(data['kalman.statePX']))
        self.gridLayout2.itemAtPosition(3,2).widget().setText("{:.5f}".format(data['kalman.statePY']))
        self.gridLayout2.itemAtPosition(3,3).widget().setText("{:.5f}".format(data['kalman.statePZ']))

    def keyPressEvent(self, event):
        if (not event.isAutoRepeat()):
            if (event.key() == QtCore.Qt.Key_Left):
                self.updateHover('y', 1)
            if (event.key() == QtCore.Qt.Key_Right):
                self.updateHover('y', -1)
            if (event.key() == QtCore.Qt.Key_Up):
                self.updateHover('x', 1)
            if (event.key() == QtCore.Qt.Key_Down):
                self.updateHover('x', -1)
            if (event.key() == QtCore.Qt.Key_A):
                self.updateHover('yaw', -70)
            if (event.key() == QtCore.Qt.Key_D):
                self.updateHover('yaw', 70)
            if (event.key() == QtCore.Qt.Key_Z):
                self.updateHover('yaw', -200)
            if (event.key() == QtCore.Qt.Key_X):
                self.updateHover('yaw', 200)
            if (event.key() == QtCore.Qt.Key_W):
                self.updateHover('height', 0.1)
            if (event.key() == QtCore.Qt.Key_S):
                self.updateHover('height', -0.1)

    def keyReleaseEvent(self, event):
        if (not event.isAutoRepeat()):
            if (event.key() == QtCore.Qt.Key_Left):
                self.updateHover('y', 0)
            if (event.key() == QtCore.Qt.Key_Right):
                self.updateHover('y', 0)
            if (event.key() == QtCore.Qt.Key_Up):
                self.updateHover('x', 0)
            if (event.key() == QtCore.Qt.Key_Down):
                self.updateHover('x', 0)
            if (event.key() == QtCore.Qt.Key_A):
                self.updateHover('yaw', 0)
            if (event.key() == QtCore.Qt.Key_D):
                self.updateHover('yaw', 0)
            if (event.key() == QtCore.Qt.Key_W):
                self.updateHover('height', 0)
            if (event.key() == QtCore.Qt.Key_S):
                self.updateHover('height', 0)
            if (event.key() == QtCore.Qt.Key_Z):
                self.updateHover('yaw', 0)
            if (event.key() == QtCore.Qt.Key_X):
                self.updateHover('yaw', 0)

    def sendHoverCommand(self):
        self.cf.commander.send_hover_setpoint(
            self.hover['x'], self.hover['y'], self.hover['yaw'],
            self.hover['height'])

    def updateHover(self, k, v):
        if (k != 'height'):
            self.hover[k] = v * SPEED_FACTOR
        else:
            self.hover[k] += v

    def disconnected(self, URI):
        print('Disconnected')
        sys.exit(1)

    def connected(self, URI):
        print('We are now connected to {}'.format(URI))
        self.cf.param.request_param_update("motion.flowStdFixed")

        log_var_config = LogConfig(name='variances', period_in_ms=100)
        log_var_config.add_variable('kalman.varX')
        log_var_config.add_variable('kalman.varY')
        log_var_config.add_variable('kalman.varZ')
        log_var_config.add_variable('kalman.varPX')
        log_var_config.add_variable('kalman.varPY')
        log_var_config.add_variable('kalman.varPZ')
        self.cf.log.add_config(log_var_config)
        log_var_config.data_received_cb.add_callback(self.log_var_callback)
        log_var_config.start()

        log_est_config = LogConfig(name='estimates', period_in_ms=100)
        log_est_config.add_variable('kalman.stateX')
        log_est_config.add_variable('kalman.stateY')
        log_est_config.add_variable('kalman.stateZ')
        log_est_config.add_variable('kalman.statePX')
        log_est_config.add_variable('kalman.statePY')
        log_est_config.add_variable('kalman.statePZ')
        self.cf.log.add_config(log_est_config)
        log_est_config.data_received_cb.add_callback(self.log_est_callback)
        log_est_config.start()
        # The definition of the logconfig can be made before connecting
        '''lp = LogConfig(name='Position', period_in_ms=100)
        lp.add_variable('stateEstimate.x')
        lp.add_variable('stateEstimate.y')
        lp.add_variable('stateEstimate.z')
        lp.add_variable('stabilizer.roll')
        lp.add_variable('stabilizer.pitch')
        lp.add_variable('stabilizer.yaw')

        try:
            self.cf.log.add_config(lp)
            lp.data_received_cb.add_callback(self.pos_data)
            lp.start()
        except KeyError as e:
            print('Could not start log configuration,'
                  '{} not found in TOC'.format(str(e)))
        except AttributeError:
            print('Could not add Position log config, bad configuration.')'''

    def closeEvent(self, event):
        if (self.cf is not None):
            self.cf.close_link()


if __name__ == '__main__':
    appQt = QtWidgets.QApplication(sys.argv)
    win = MainWindow(URI)
    win.show()
    appQt.exec()
