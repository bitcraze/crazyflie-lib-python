# -*- coding: utf-8 -*-
#
#     ||          ____  _ __
#  +------+      / __ )(_) /_______________ _____  ___
#  | 0xBC |     / __  / / __/ ___/ ___/ __ `/_  / / _ \
#  +------+    / /_/ / / /_/ /__/ /  / /_/ / / /_/  __/
#   ||  ||    /_____/_/\__/\___/_/   \__,_/ /___/\___/
#
#  Copyright (C) 2016 Bitcraze AB
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
import time
from threading import Thread


class AsyncCallbackCaller:

    def __init__(self, cb=None, delay=0, args=(), kwargs={}):
        self.caller = cb
        self.delay = delay
        self.args = args
        self.kwargs = kwargs
        self.call_count = 0

    def trigger(self, *args, **kwargs):
        self.call_count += 1
        Thread(target=self._make_call).start()

    def call_and_wait(self):
        thread = Thread(target=self._make_call)
        thread.start()
        thread.join()

    def _make_call(self):
        time.sleep(self.delay)
        self.caller.call(*self.args, **self.kwargs)
