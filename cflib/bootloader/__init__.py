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
Bootloading utilities for the Crazyflie.
"""
import json
import logging
import sys
import time
import zipfile

from .boottypes import BootVersion
from .boottypes import TargetTypes
from .cloader import Cloader

logger = logging.getLogger(__name__)

__author__ = 'Bitcraze AB'
__all__ = ['Bootloader']


class Bootloader:
    """Bootloader utility for the Crazyflie"""

    def __init__(self, clink=None):
        """Init the communication class by starting to communicate with the
        link given. clink is the link address used after resetting to the
        bootloader.

        The device is actually considered in firmware mode.
        """
        self.clink = clink
        self.in_loader = False

        self.page_size = 0
        self.buffer_pages = 0
        self.flash_pages = 0
        self.start_page = 0
        self.cpuid = 'N/A'
        self.error_code = 0
        self.protocol_version = 0

        # Outgoing callbacks for progress
        # int
        self.progress_cb = None
        # msg
        self.error_cb = None
        # bool
        self.in_bootloader_cb = None
        # Target
        self.dev_info_cb = None

        # self.dev_info_cb.add_callback(self._dev_info)
        # self.in_bootloader_cb.add_callback(self._bootloader_info)

        self._boot_plat = None

        self._cload = Cloader(clink,
                              info_cb=self.dev_info_cb,
                              in_boot_cb=self.in_bootloader_cb)

    def start_bootloader(self, warm_boot=False):
        if warm_boot:
            self._cload.open_bootloader_uri(self.clink)
            started = self._cload.reset_to_bootloader(TargetTypes.NRF51)
            if started:
                started = self._cload.check_link_and_get_info()
        else:
            uri = self._cload.scan_for_bootloader()

            # Workaround for libusb on Windows (open/close too fast)
            time.sleep(1)

            if uri:
                self._cload.open_bootloader_uri(uri)
                started = self._cload.check_link_and_get_info()
            else:
                started = False

        if started:
            self.protocol_version = self._cload.protocol_version

            if (self.protocol_version == BootVersion.CF1_PROTO_VER_0 or
                    self.protocol_version == BootVersion.CF1_PROTO_VER_1):
                # Nothing more to do
                pass
            elif self.protocol_version == BootVersion.CF2_PROTO_VER:
                self._cload.request_info_update(TargetTypes.NRF51)
            else:
                print('Bootloader protocol 0x{:X} not '
                      'supported!'.self.protocol_version)

        return started

    def get_target(self, target_id):
        return self._cload.request_info_update(target_id)

    def read_cf1_config(self):
        """Read a flash page from the specified target"""
        target = self._cload.targets[0xFF]
        config_page = target.flash_pages - 1

        return self._cload.read_flash(addr=0xFF, page=config_page)

    def write_cf1_config(self, data):
        target = self._cload.targets[0xFF]
        config_page = target.flash_pages - 1

        to_flash = {'target': target, 'data': data, 'type': 'CF1 config',
                    'start_page': config_page}

        self._internal_flash(target=to_flash)

    def verify(self, filename, targets):
        for target in targets:
            if TargetTypes.from_string(target) not in self._cload.targets:
                print('Target {} not found by bootloader'.format(target))
                return False

        files_to_verify = ()
        if zipfile.is_zipfile(filename):
            # Read the manifest (don't forget to check so there is one!)
            try:
                zf = zipfile.ZipFile(filename)
                js = zf.read('manifest.json').decode('UTF-8')
                j = json.loads(js)
                files = j['files']
                platform_id = self._get_platform_id()
                files_for_platform = self._filter_platform(files, platform_id)
                if len(targets) == 0:
                    targets = self._extract_targets_from_manifest_files(
                        files_for_platform)

                zip_targets = self._extract_zip_targets(files_for_platform)
            except KeyError as e:
                print(e)
                print('No manifest.json in {}'.format(filename))
                return False

            try:
                # Match and create targets
                for target in targets:
                    t = targets[target]
                    for type in t:
                        file_to_verify = {}
                        current_target = '{}-{}'.format(target, type)
                        file_to_verify['type'] = type
                        # Read the data, if this fails we bail
                        file_to_verify['target'] = self._cload.targets[
                            TargetTypes.from_string(target)]
                        file_to_verify['data'] = zf.read(
                            zip_targets[target][type]['filename'])
                        file_to_verify['start_page'] = file_to_verify[
                            'target'].start_page
                        files_to_verify += (file_to_verify,)
            except KeyError as e:
                print('Could not find a file for {} in {}'.format(
                    current_target, filename))
                return False
        else:
            if len(targets) != 1:
                print('Not an archive, must supply one target to verify')
            else:
                file_to_verify = {}
                file_to_verify['type'] = 'binary'
                f = open(filename, 'rb')
                for t in targets:
                    file_to_verify['target'] = self._cload.targets[
                        TargetTypes.from_string(t)]
                    file_to_verify['type'] = targets[t][0]
                    file_to_verify['start_page'] = file_to_verify[
                        'target'].start_page
                file_to_verify['data'] = f.read()
                f.close()
                files_to_verify += (file_to_verify,)

        if not self.progress_cb:
            print('')

        # create batch data list
        batch_list = []
        batch_index = []
        datalist = {}
        file_info = {}
        loaded_first = True
        for target in files_to_verify:
            image = target['data']
            t_data = target['target']
            page_number = int((len(image) - 1) / t_data.page_size) + 1

            if loaded_first:
                first_file = t_data.addr
                # print(image[10240-26: 10240+26])
                loaded_first = False

            file_info[t_data.addr] = (len(image),
                                      page_number, target['start_page'])
            datalist[t_data.addr] = bytearray(len(image))

            for i in range(0, page_number):
                for x in range(0, int(t_data.page_size / 25.0)+1):
                    tup = (t_data.addr, i+target['start_page'], x)
                    batch_list.append(tup)
                    batch_index.append(1)

        factor = (100.0 * 1024 / 41) / (file_info[255][0] + file_info[254][1])
        progress = 0
        count = 0

        while not sum(batch_index) == 0:
            count += 1

            # something is wrong
            if count > 7:
                print("Go too long")
                print("Remaining index")
                ctr = 0
                for index in range(len(batch_index)):
                    if batch_index[index] == 1:
                        print(batch_list[index], index)
                print(file_info)
                print(first_file)
                return False

            for index in range(len(batch_index)):

                if batch_index[index] == 1:

                    addr = batch_list[index][0]
                    page = batch_list[index][1]
                    page_index = batch_list[index][2]

                    back_data = self._cload.batch_helper(addr, page,
                                                         page_index)

                    if back_data is not None:
                        temp_pk = back_data[0]

                        if temp_pk[1] == (0x1C) and \
                           (temp_pk[0] == 255 or temp_pk[0] == 254):
                            this_file = temp_pk[0]
                            back_element = temp_pk[3]
                            start_page = file_info[this_file][2]

                            place = (back_element +
                                    (temp_pk[2]-start_page))*1024

                            if back_element == 1000:
                                datalist[this_file][place: place+24] \
                                    = back_data[1][6:30]
                            else:
                                datalist[this_file][place: place+25] \
                                    = back_data[1][6:]

                            print("received: segment/page #{}/{}".format(
                                  int(back_element/25),
                                  temp_pk[2]-start_page))

                            if this_file == first_file:
                                batch_index[
                                    (int(back_element/25) +
                                     (temp_pk[2]-start_page)*41)
                                ] = 0
                            else:
                                batch_index[
                                    (int(back_element/25) +
                                     (file_info[first_file][1] +
                                      temp_pk[2]-start_page)*41)
                                ] = 0

                        progress += factor
                        if self.progress_cb:
                            self.progress_cb(
                                'Data page {} is verified'.format(page),
                                int(progress))

        for target in files_to_verify:
            if not target['data'] == \
                    datalist[target['target'].addr][:len(target['data'])]:
                for x in range(len(target['data'])):
                    if target['data'][x] != datalist[target['target'].addr][x]:
                        return False
        print("Success")
        return True

    def flash(self, filename, targets, verify):
        for target in targets:
            if TargetTypes.from_string(target) not in self._cload.targets:
                print('Target {} not found by bootloader'.format(target))
                return False

        files_to_flash = ()
        if zipfile.is_zipfile(filename):
            # Read the manifest (don't forget to check so there is one!)
            try:
                zf = zipfile.ZipFile(filename)
                js = zf.read('manifest.json').decode('UTF-8')
                j = json.loads(js)
                files = j['files']
                platform_id = self._get_platform_id()
                files_for_platform = self._filter_platform(files, platform_id)
                if len(targets) == 0:
                    targets = self._extract_targets_from_manifest_files(
                        files_for_platform)

                zip_targets = self._extract_zip_targets(files_for_platform)
            except KeyError as e:
                print(e)
                print('No manifest.json in {}'.format(filename))
                return

            try:
                # Match and create targets
                for target in targets:
                    t = targets[target]
                    for type in t:
                        file_to_flash = {}
                        current_target = '{}-{}'.format(target, type)
                        file_to_flash['type'] = type
                        # Read the data, if this fails we bail
                        file_to_flash['target'] = self._cload.targets[
                            TargetTypes.from_string(target)]
                        file_to_flash['data'] = zf.read(
                            zip_targets[target][type]['filename'])
                        file_to_flash['start_page'] = file_to_flash[
                            'target'].start_page
                        files_to_flash += (file_to_flash,)
            except KeyError as e:
                print('Could not find a file for {} in {}'.format(
                    current_target, filename))
                return False

        else:
            if len(targets) != 1:
                print('Not an archive, must supply one target to flash')
            else:
                file_to_flash = {}
                file_to_flash['type'] = 'binary'
                f = open(filename, 'rb')
                for t in targets:
                    file_to_flash['target'] = self._cload.targets[
                        TargetTypes.from_string(t)]
                    file_to_flash['type'] = targets[t][0]
                    file_to_flash['start_page'] = file_to_flash[
                        'target'].start_page
                file_to_flash['data'] = f.read()
                f.close()
                files_to_flash += (file_to_flash,)

        if not self.progress_cb:
            print('')

        file_counter = 0
        for target in files_to_flash:
            file_counter += 1
            self._internal_flash(
                target, file_counter, len(files_to_flash), verify
            )

        batch_list = []
        batch_index = []
        datalist = {}
        file_info = {}
        loaded_first = True
        for target in files_to_flash:
            image = target['data']
            t_data = target['target']
            page_number = int((len(image) - 1) / t_data.page_size) + 1

            if loaded_first:
                first_file = t_data.addr
                loaded_first = False

            file_info[t_data.addr] = (len(image),
                                      page_number, target['start_page'])
            datalist[t_data.addr] = bytearray(len(image))

            for i in range(0, page_number):
                for x in range(0, int(t_data.page_size / 25.0)+1):
                    tup = (t_data.addr, i+target['start_page'], x)
                    batch_list.append(tup)
                    batch_index.append(1)

        factor = 100.0 / len(batch_index)
        progress = 0
        count = 0

        while not sum(batch_index) == 0:
            count += 1

            # something is wrong
            if count > 7:
                print("Go too long")
                print("Remaining index")
                ctr = 0
                for index in range(len(batch_index)):
                    if batch_index[index] == 1:
                        print(batch_list[index], index)
                print(file_info)
                print(first_file)
                return False

            for index in range(len(batch_index)):

                if batch_index[index] == 1:

                    addr = batch_list[index][0]
                    page = batch_list[index][1]
                    page_index = batch_list[index][2]

                    back_data = self._cload.batch_helper(
                        addr, page, page_index
                    )

                    if back_data is not None:
                        temp_pk = back_data[0]

                        if temp_pk[1] == (0x1C) and \
                           (temp_pk[0] == 255 or temp_pk[0] == 254):
                            this_file = temp_pk[0]
                            back_element = temp_pk[3]
                            start_page = file_info[this_file][2]

                            place = back_element + \
                                (temp_pk[2] - start_page)*1024

                            if back_element == 1000:
                                datalist[this_file][place: place+24]\
                                    = back_data[1][6:30]
                            else:
                                datalist[this_file][place: place+25]\
                                    = back_data[1][6:]

                            print("received: segment/page #{}/{}".format(
                                  int(back_element/25),
                                  temp_pk[2]-start_page))

                            if this_file == first_file:
                                batch_index[
                                    int(back_element/25) +
                                    (temp_pk[2]-start_page)*41
                                ] = 0
                            else:
                                batch_index[
                                    int(back_element/25) +
                                    (file_info[first_file][1] +
                                     temp_pk[2]-start_page)*41
                                ] = 0

                        progress += factor
                        if self.progress_cb:
                            self.progress_cb(
                                'Data page {} is verified'.format(
                                    page), int(progress))

        for target in files_to_flash:
            if not target['data'] == \
                    datalist[target['target'].addr][:len(target['data'])]:
                for x in range(len(target['data'])):
                    if target['data'][x] != datalist[target['target'].addr][x]:
                        return False
        print("Verified, Success")
        return True

    def _filter_platform(self, files, platform_id):
        result = {}
        for file in files:
            file_info = files[file]
            file_platform = file_info['platform']
            if platform_id == file_platform:
                result[file] = file_info
        return result

    def _extract_zip_targets(self, files):
        zip_targets = {}
        for file in files:
            file_name = file
            file_info = files[file]
            file_target = file_info['target']
            file_type = file_info['type']
            if file_target not in zip_targets:
                zip_targets[file_target] = {}
            zip_targets[file_target][file_type] = {
                'filename': file_name}
        return zip_targets

    def _extract_targets_from_manifest_files(self, files):
        targets = {}
        for file in files:
            file_info = files[file]
            file_target = file_info['target']
            file_type = file_info['type']
            if file_target in targets:
                targets[file_target] += (file_type,)
            else:
                targets[file_target] = (file_type,)

        return targets

    def reset_to_firmware(self):
        if self._cload.protocol_version == BootVersion.CF2_PROTO_VER:
            self._cload.reset_to_firmware(TargetTypes.NRF51)
        else:
            self._cload.reset_to_firmware(TargetTypes.STM32)

    def close(self):
        if self._cload:
            self._cload.close()

    def _internal_verify(self, target, current_file_number=1, total_files=1):

        image = target['data']
        t_data = target['target']
        start_page = target['start_page']

        # If used from a UI we need some extra things for reporting progress
        factor = (100.0 * t_data.page_size) / len(image)
        progress = 0

        if self.progress_cb:
            self.progress_cb(
                '({}/{}) Starting...'.format(current_file_number, total_files),
                int(progress))
        else:
            sys.stdout.write(
                'Verifying {} of {} to {} ({}): '.format(
                    current_file_number, total_files,
                    TargetTypes.to_string(t_data.id), target['type']))
            sys.stdout.flush()

        if not self.progress_cb:
            logger.info(('%d bytes (%d pages) ' % (
                (len(image) - 1), int(len(image) / t_data.page_size) + 1)))
            sys.stdout.write(('%d bytes (%d pages) ' % (
                (len(image) - 1), int(len(image) / t_data.page_size) + 1)))
            sys.stdout.flush()

        # For each page
        page_number = int((len(image) - 1) / t_data.page_size) + 1
        for i in range(0, page_number):
            progress += factor
            # Load the data
            file_data_page = bytearray()
            if ((i + 1) * t_data.page_size) > len(image):
                file_data_page = image[i * t_data.page_size:]
                current_filedata_size = len(image) - i * t_data.page_size
            else:
                file_data_page = image[
                    i * t_data.page_size: (i + 1) * t_data.page_size
                ]
                current_filedata_size = t_data.page_size
            if self.progress_cb:
                self.progress_cb('({}/{}) Verifying data page {}/{}...'.format(
                    current_file_number,
                    total_files,
                    i,
                    page_number),
                    int(progress))
            data_page = bytearray()
            data_page = self._cload.batch_read_flash(
                t_data.addr, start_page + i
            )

            if not data_page[0:current_filedata_size] \
                    == file_data_page[0:current_filedata_size]:
                print('wrong!')
                progress = 100
                if self.progress_cb:
                    self.progress_cb(
                        'Verification complete: ({}/{}) data page ({}/{}) \
                        is not successfully flashed '.format(
                        current_file_number,
                        total_files,
                        i,
                        page_number),
                        int(progress))
                else:
                    print('\nError during verify operation (code %d). '
                          'Maybe wrong radio link?' %
                          self._cload.error_code)
                return False

        if self.progress_cb:
            self.progress_cb(
                '({}/{}) Verification complete: \
                This file is successfully flashed. '.format(
                current_file_number,
                total_files),
                int(100))
        else:
            print('')
        return True

    def _internal_flash(self, target, current_file_number=1,
                        total_files=1, verify=False):

        image = target['data']
        t_data = target['target']
        start_page = target['start_page']

        # If used from a UI we need some extra things for reporting progress
        factor = (100.0 * t_data.page_size) / len(image)
        progress = 0
        page_number = (int((len(image) - 1)
                       / t_data.page_size)) + 1
        if self.progress_cb:
            self.progress_cb(
                '({}/{}) Starting...'.format(current_file_number,
                                             total_files),
                int(progress))
        else:
            sys.stdout.write(
                'Flashing {} of {} to {} ({}): '.format(
                    current_file_number, total_files,
                    TargetTypes.to_string(t_data.id),
                    target['type']))
            sys.stdout.flush()

        if len(image) > ((t_data.flash_pages - start_page) *
                         t_data.page_size):
            if self.progress_cb:
                self.progress_cb(
                    'Error: Not enough space to \
                    flash the image file.',
                    int(progress))
            else:
                print('Error: Not enough space to \
                    flash the image file.')
            raise Exception()

        if not self.progress_cb:
            logger.info(('%d bytes (%d pages) ' % (
                (len(image) - 1),
                int(len(image) / t_data.page_size) + 1)))
            sys.stdout.write(('%d bytes (%d pages) ' % (
                (len(image) - 1),
                int(len(image) / t_data.page_size) + 1)))
            sys.stdout.flush()

        # For each page
        ctr = 0  # Buffer counter
        for i in range(0, page_number):
            # Load the buffer
            if ((i + 1) * t_data.page_size) > len(image):
                self._cload.upload_buffer(
                    t_data.addr, ctr, 0,
                    image[i * t_data.page_size:])
            else:
                self._cload.upload_buffer(
                    t_data.addr, ctr, 0,
                    image[i * t_data.page_size: (i + 1) * t_data.page_size])
            ctr += 1

            if self.progress_cb:
                progress += factor
                self.progress_cb('({}/{}) Uploading buffer to {}...'.format(
                    current_file_number,
                    total_files,
                    TargetTypes.to_string(t_data.id)),

                    int(progress))
            else:
                sys.stdout.write('.')
                sys.stdout.flush()

            # Flash when the complete buffers are full
            if ctr >= t_data.buffer_pages:
                if self.progress_cb:
                    self.progress_cb('({}/{}) Writing buffer to {}...'.format(
                        current_file_number,
                        total_files,
                        TargetTypes.to_string(t_data.id)),

                        int(progress))
                else:
                    sys.stdout.write('%d' % ctr)
                    sys.stdout.flush()
                if self._cload.write_flash(t_data.addr, 0,
                                           start_page + i - (ctr - 1),
                                           ctr):

                    if verify:
                        for page in range(0, ctr):
                            print('verifying sub page {}/{}'.format(page + 1,
                                                                    ctr))
                            data_page = bytearray()
                            file_page = bytearray()
                            current_page = i - (ctr - 1) + page

                            if ((current_page + 1) * t_data.page_size) \
                                    > len(image):
                                file_data_page = (
                                    image[current_page * t_data.page_size:])
                                current_filedata_size = (
                                    len(image) - current_page*t_data.page_size
                                )
                            else:
                                file_data_page = image[
                                    current_page * t_data.page_size:
                                    (current_page + 1) * t_data.page_size
                                ]
                                current_filedata_size = t_data.page_size
                            data_page = self._cload.batch_read_flash(
                                t_data.addr, start_page + current_page
                            )
                            if self.progress_cb:
                                self.progress_cb('({}/{}) Verifying \
                                    data page ({}/{})...'.format(
                                    current_file_number,
                                    total_files,
                                    i - (ctr - 1) + page,
                                    page_number),
                                    int(progress))
                            retry = 10
                            while not data_page[0:current_filedata_size] == \
                                file_data_page[0:current_filedata_size] \
                                    and retry > 0:
                                print('Resending...')
                                print('Retry:', retry)
                                self._cload.write_flash(
                                    t_data.addr, page,
                                    start_page + i - (ctr - 1) + page, 1
                                )
                                data_page = self._cload.batch_read_flash(
                                    t_data.addr,
                                    start_page + i - (ctr - 1) + page
                                )
                                retry -= 1

                                if self.progress_cb:
                                    print('reflashing data page {}/{}'.format(
                                        i - (ctr - 1) + page, page_number)
                                    )
                                    self.progress_cb('({}/{}) Reflashing \
                                        data page {}/{}...'.format(
                                        current_file_number,
                                        total_files,
                                        i - (ctr - 1) + page,
                                        page_number),
                                        int(progress))
                                if retry == 0:
                                    if self.progress_cb:
                                        self.progress_cb(
                                            'Error during flash operation',
                                            int(progress))
                                    print('not able to reflash, \
                                          probably some problem \
                                          in uploading buffer?')
                                    raise Exception()

                else:
                    if self.progress_cb:
                        self.progress_cb(
                            'Error during flash operation (code %d)'.format(
                                self._cload.error_code),
                            int(progress))
                    else:
                        print('\nError during flash operation (code %d). '
                              'Maybe wrong radio link?' %
                              self._cload.error_code)
                    raise Exception()
                ctr = 0

        if ctr > 0:
            if self.progress_cb:
                self.progress_cb('({}/{}) Writing buffer to {}...'.format(
                    current_file_number,
                    total_files,
                    TargetTypes.to_string(t_data.id)),
                    int(progress))
            else:
                sys.stdout.write('%d' % ctr)
                sys.stdout.flush()
            if self._cload.write_flash(
                    t_data.addr, 0,
                    (start_page +
                     (int((len(image) - 1) / t_data.page_size)) -
                     (ctr - 1)), ctr):

                if verify:
                    for page in range(0, ctr):
                        print('verifying page {}/{}'.format(
                            page + 1, ctr)
                        )
                        data_page = bytearray()
                        file_page = bytearray()
                        current_page = \
                            (int((len(image)-1) / t_data.page_size)) \
                            - (ctr - 1) + page
                        data_page = self._cload.batch_read_flash(
                            t_data.addr, start_page + current_page
                        )
                        if ((current_page + 1)*t_data.page_size) > len(image):
                            file_data_page = image[
                                current_page * t_data.page_size:
                            ]
                            current_filedata_size = (
                                len(image) - current_page * t_data.page_size
                            )
                        else:
                            file_data_page = image[
                                current_page * t_data.page_size:
                                (current_page + 1) * t_data.page_size
                            ]
                            current_filedata_size = t_data.page_size
                        if self.progress_cb:
                            self.progress_cb('({}/{}) Verifying \
                                data page {}/{}...'.format(
                                current_file_number,
                                total_files,
                                i - (ctr - 1) + page,
                                page_number),
                                int(progress))
                        retry = 10
                        while not data_page[0:current_filedata_size] \
                                == file_data_page[0:current_filedata_size] \
                                and retry > 0:
                            print('Resending...')
                            print('retry:', retry)
                            self._cload.write_flash(
                                t_data.addr, page,
                                start_page + i - (ctr - 1) + page, 1
                            )
                            data_page = self._cload.batch_read_flash(
                                t_data.addr,
                                start_page + i - (ctr - 1) + page
                            )
                            retry -= 1
                            if self.progress_cb:
                                print('reflashing data page {}/{}'.format(
                                    i - (ctr - 1) + page, page_number)
                                )
                                self.progress_cb('({}/{}) Reflashing \
                                    data page {}/{}...'.format(
                                    current_file_number,
                                    total_files,
                                    i - (ctr - 1) + page,
                                    page_number),
                                    int(progress))
            else:
                if self.progress_cb:
                    self.progress_cb(
                        'Error during flash operation (code %d)'.format(
                            self._cload.error_code),
                        int(progress))
                else:
                    print('\nError during flash operation (code %d). Maybe'
                          ' wrong radio link?' % self._cload.error_code)
                raise Exception()

        if self.progress_cb:
            if verify:
                self.progress_cb(
                    '({}/{}) Flashing and \
                    verification done!'.format(current_file_number,
                                               total_files),
                    int(100))
            else:
                self.progress_cb(
                    '({}/{}) Flashing  done!'.format(current_file_number,
                                                     total_files),
                    int(100))
        else:
            print('')

    def _get_platform_id(self):
        """Get platform identifier used in the zip manifest for curr copter"""
        identifier = 'cf1'
        if (BootVersion.is_cf2(self.protocol_version)):
            identifier = 'cf2'

        return identifier
