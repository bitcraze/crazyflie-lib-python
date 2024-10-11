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
# You should have received a copy of the GNU General Public License
# along with this program. If not, see <https://www.gnu.org/licenses/>.
"""
Bootloading utilities for the Crazyflie.
"""
import json
import logging
import sys
import time
import zipfile
from collections import namedtuple
from typing import Callable
from typing import List
from typing import NoReturn
from typing import Optional
from typing import Tuple

from packaging.version import Version

from .boottypes import BootVersion
from .boottypes import TargetTypes
from .cloader import Cloader
from cflib.crazyflie import Crazyflie
from cflib.crazyflie.mem import deck_memory
from cflib.crazyflie.mem import MemoryElement
from cflib.crazyflie.syncCrazyflie import SyncCrazyflie
from cflib.utils.power_switch import PowerSwitch

logger = logging.getLogger(__name__)

__author__ = 'Bitcraze AB'
__all__ = ['Bootloader']

Target = namedtuple('Target', ['platform', 'target', 'type', 'provides', 'requires'])
FlashArtifact = namedtuple('FlashArtifact', ['content', 'target', 'release'])


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

        self.warm_booted = False

        # Outgoing callbacks for progress and flash termination
        self.progress_cb = None  # type: Optional[Callable[[str, int], None]]
        self.error_cb = None  # type: Optional[Callable[[str], None]]
        self.terminate_flashing_cb = None  # type: Optional[Callable[[], bool]]

        self._boot_plat = None

        self._cload = Cloader(clink,
                              info_cb=None,
                              in_boot_cb=None)

    def start_bootloader(self, warm_boot=False, cf=None):
        self.warm_booted = warm_boot

        if warm_boot:
            if cf is not None and cf.link:
                cf.close_link()
            self._cload.open_bootloader_uri(self.clink)
            started = self._cload.reset_to_bootloader(TargetTypes.NRF51)
            if started:
                started = self._cload.check_link_and_get_info()
        else:
            if not self._cload.link:
                uri = self._cload.scan_for_bootloader()

                # Workaround for libusb on Windows (open/close too fast)
                time.sleep(1)

                if uri:
                    self._cload.open_bootloader_uri(uri)
                    started = self._cload.check_link_and_get_info()
                else:
                    started = False
            else:
                started = True
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
                      'supported!'.format(self.protocol_version))

        return started

    def get_target(self, target_id):
        return self._cload.request_info_update(target_id)

    def _get_current_nrf51_sd_version(self):
        if self._cload.targets[TargetTypes.NRF51].start_page == 88:
            return 'sd-s110'
        elif self._cload.targets[TargetTypes.NRF51].start_page == 108:
            return 'sd-s130'
        else:
            raise Exception('Unknown soft device running on nRF51')

    def _get_required_nrf51_sd_version(self, flash_artifacts: List[FlashArtifact]):
        required_nrf_sd_version = None
        for a in flash_artifacts:
            if a.target.target == 'nrf51':
                for r in a.target.requires:
                    if required_nrf_sd_version is None:
                        required_nrf_sd_version = r
                    if required_nrf_sd_version != r:
                        raise Exception('Cannot flash nRF51, conflicting requirements: {} and {}'.format(
                            required_nrf_sd_version, r))

        return required_nrf_sd_version

    def _get_provided_nrf51_sd_version(self, flash_artifacts: List[FlashArtifact]):
        provided_nrf_sd_version = None
        for a in flash_artifacts:
            if a.target.target == 'nrf51':
                for r in a.target.provides:
                    if provided_nrf_sd_version is None:
                        provided_nrf_sd_version = r
                    if provided_nrf_sd_version != r:
                        raise Exception('Cannot flash nRF51, conflicting requirements: {} and {}'.format(
                            provided_nrf_sd_version, r))

        return provided_nrf_sd_version

    def _get_provided_nrf51_bl_version(self, flash_artifacts: List[FlashArtifact]):
        provided_nrf_bl_version = None
        for a in flash_artifacts:
            if a.target.target == 'nrf51' and a.target.type == 'bootloader+softdevice':
                if provided_nrf_bl_version is None:
                    provided_nrf_bl_version = a.release
                else:
                    raise Exception('One and only one bootloader+softdevice in zip file supported')

        return provided_nrf_bl_version

    def flash(self, filename: str, targets: List[Target], cf=None, enable_console_log: Optional[bool] = False):
        # Separate flash targets from decks
        platform = self._get_platform_id()
        flash_targets = [t for t in targets if t.platform == platform]
        deck_targets = [t for t in targets if t.platform == 'deck']

        # Fetch artifacts from source file
        artifacts = self._get_flash_artifacts_from_zip(filename)
        if len(artifacts) == 0:
            if len(targets) == 1:
                content = open(filename, 'br').read()
                artifacts = [FlashArtifact(content, targets[0], None)]
            else:
                raise (Exception('Cannot flash a .bin to more than one target!'))

        # Separate artifacts for flash and decks
        flash_artifacts = [a for a in artifacts if a.target.platform == platform]
        deck_artifacts = [a for a in artifacts if a.target.platform == 'deck']

        # Handle the special case of flashing soft device and bootloader for nRF51
        current_nrf_sd_version = self._get_current_nrf51_sd_version()
        required_nrf_sd_version = self._get_required_nrf51_sd_version(flash_artifacts)
        provided_nrf_sd_version = self._get_provided_nrf51_sd_version(flash_artifacts)
        update_contains_nrf_sd = any(x.target.type == 'bootloader+softdevice' for x in flash_artifacts)
        current_nrf_bl_version = None
        if self._cload.targets[TargetTypes.NRF51].version is not None:
            current_nrf_bl_version = Version(str(self._cload.targets[TargetTypes.NRF51].version))
        provided_nrf_bl_version = None
        if self._get_provided_nrf51_bl_version(flash_artifacts) is not None:
            provided_nrf_bl_version = Version(self._get_provided_nrf51_bl_version(flash_artifacts))

        print('nRF51 has: {} and requires {} and upgrade provides {}. Current bootloader version is [{}] and upgrade '
              'provides [{}]'.format(
                  current_nrf_sd_version, required_nrf_sd_version, provided_nrf_sd_version,
                  current_nrf_bl_version, provided_nrf_bl_version)
              )

        if required_nrf_sd_version is not None and \
                current_nrf_sd_version != required_nrf_sd_version and \
                provided_nrf_sd_version != required_nrf_sd_version:
            raise Exception('Cannot flash nRF51: We have sd {}, need {} and have a zip with {}'.format(
                current_nrf_sd_version, required_nrf_sd_version, provided_nrf_sd_version))

        # To avoid always flashing the bootloader and soft device (these might never change again) first check
        # if we really need to. The original version of the bootloader is reported as None.
        should_flash_nrf_sd = True
        if current_nrf_sd_version == required_nrf_sd_version and current_nrf_bl_version == provided_nrf_bl_version:
            should_flash_nrf_sd = False
        elif provided_nrf_sd_version is None and not update_contains_nrf_sd:
            should_flash_nrf_sd = False

        if should_flash_nrf_sd:
            print('Should flash nRF soft device')
            rf51_sdbl_list = [x for x in flash_artifacts if x.target.type == 'bootloader+softdevice']
            if len(rf51_sdbl_list) != 1:
                raise Exception('Only support for one and only one bootloader+softdevice in zip file')
            nrf51_sdbl = rf51_sdbl_list[0]

            nrf_info = self._cload.targets[TargetTypes.NRF51]
            # During bootloader update part of the firmware will be erased. If we're
            # only flashing the bootloader and no firmware we should make sure the bootloader
            # stays in bootloader mode and doesn't try to start the broken firmware, this is
            # done by erasing the first page of the firmware.
            self._internal_flash(FlashArtifact([0xFF] * nrf_info.page_size, nrf51_sdbl.target, None))
            page = nrf_info.flash_pages - (len(nrf51_sdbl.content) // nrf_info.page_size)
            self._internal_flash(artifact=nrf51_sdbl, page_override=page)

            self._cload.reset_to_bootloader(TargetTypes.NRF51)
            uri = self._cload.link.uri
            self._cload.close()
            print('Closing bootloader link and reconnecting to new bootloader (' + uri + ')')
            self._cload = Cloader(uri,
                                  info_cb=None,
                                  in_boot_cb=None)
            self._cload.open_bootloader_uri(uri)
            print('Reconnected to new bootloader')
            self._cload.check_link_and_get_info()
            self._cload.request_info_update(TargetTypes.NRF51)
        else:
            print('No need to flash nRF soft device')

        # Remove the softdevice+bootloader from the list of artifacts to flash
        flash_artifacts = [a for a in flash_artifacts if a.target.type !=
                           'bootloader+softdevice']  # Also filter for nRF51 here?

        # Flash the MCU flash
        if len(targets) == 0 or len(flash_targets) > 0:
            self._flash_flash(flash_artifacts, flash_targets)

        # Flash the decks
        deck_update_msg = 'Deck update skipped.'
        if len(targets) == 0 or len(deck_targets) > 0:
            # only in warm boot
            if self.warm_booted:
                if self.progress_cb:
                    self.progress_cb('Restarting firmware to update decks.', int(0))

                # Reset to firmware mode
                self.reset_to_firmware()
                self.close()
                time.sleep(3)

                # Flash all decks and reboot after each deck
                current_index = 0
                while current_index != -1:
                    current_index = self._flash_deck_incrementally(deck_artifacts, deck_targets, current_index,
                                                                   enable_console_log=enable_console_log)
                    if self.progress_cb:
                        self.progress_cb('Deck updated! Restarting...', int(100))
                    if current_index != -1:
                        PowerSwitch(self.clink).reboot_to_fw()
                        time.sleep(3)

                # Put the crazyflie back in Bootloader mode to exit the function in the same state we entered it
                self.start_bootloader(warm_boot=True, cf=cf)

                deck_update_msg = 'Deck update complete.'
            else:
                print('Skipping updating deck on coldboot')
                deck_update_msg = 'Deck update skipped in ColdBoot mode.'

        if self.progress_cb:
            self.progress_cb(
                f'({len(flash_artifacts)}/{len(flash_artifacts)}) Flashing done! {deck_update_msg}',
                int(100))
        else:
            print('')

    def flash_full(self, cf: Optional[Crazyflie] = None,
                   filename: Optional[str] = None,
                   warm: bool = True,
                   targets: Optional[Tuple[str, ...]] = None,
                   info_cb: Optional[Callable[[int, TargetTypes], NoReturn]] = None,
                   progress_cb: Optional[Callable[[str, int], NoReturn]] = None,
                   terminate_flash_cb: Optional[Callable[[], bool]] = None,
                   enable_console_log: Optional[bool] = False):
        """
        Flash .zip or bin .file to list of targets.
        Reset to firmware when done.
        """
        if progress_cb is not None:
            self.progress_cb = progress_cb
        if terminate_flash_cb is not None:
            self.terminate_flashing_cb = terminate_flash_cb

        if not self.start_bootloader(warm_boot=warm, cf=cf):
            raise Exception('Could not connect to bootloader')

        if info_cb is not None:
            connected = (self.get_target(TargetTypes.STM32),)
            if self.protocol_version == BootVersion.CF2_PROTO_VER:
                connected += (self.get_target(TargetTypes.NRF51),)
            info_cb(self.protocol_version, connected)

        if filename is not None:
            self.flash(filename, targets, cf, enable_console_log=enable_console_log)
            self.reset_to_firmware()

    def _get_flash_artifacts_from_zip(self, filename):
        if not zipfile.is_zipfile(filename):
            return []

        zf = zipfile.ZipFile(filename)

        manifest = zf.read('manifest.json').decode('utf8')
        manifest = json.loads(manifest)

        if manifest['version'] > 2:
            raise Exception('Wrong manifest version')

        print('Found manifest version: {}'.format(manifest['version']))

        flash_artifacts = []
        add_legacy_nRF51_s110 = False
        for (file, metadata) in manifest['files'].items():
            content = zf.read(file)

            # Handle version 1 of manifest where prerequisites for nRF soft-devices are not specified
            requires = [] if 'requires' not in metadata else metadata['requires']
            provides = [] if 'provides' not in metadata else metadata['provides']
            if len(requires) == 0 and metadata['target'] == 'nrf51' and metadata['type'] == 'fw':
                requires.append('sd-s110')
                # If there is no requires for the nRF51 fw target then we also need the legacy s110
                # so add this to the file list afterwards
                add_legacy_nRF51_s110 = True

            target = Target(metadata['platform'], metadata['target'], metadata['type'],
                            provides, requires)
            flash_artifacts.append(FlashArtifact(content, target, metadata['release']))

        if add_legacy_nRF51_s110:
            print('Legacy format detected for manifest, adding s110+bl binary from distro')
            from importlib.resources import read_binary
            content = read_binary('cflib.resources.binaries', 'nrf51-s110-and-bl.bin')
            target = Target('cf2', 'nrf51', 'bootloader+softdevice', ['sd-s110'], [])
            release = None
            flash_artifacts.append(FlashArtifact(content, target, release))

        return flash_artifacts

    def _flash_flash(self, artifacts: List[FlashArtifact], targets: List[Target]):
        for (i, artifact) in enumerate(artifacts):
            self._internal_flash(artifact, i + 1, len(artifacts))

    def reset_to_firmware(self) -> bool:
        status = False
        if self._cload.protocol_version == BootVersion.CF2_PROTO_VER:
            status = self._cload.reset_to_firmware(TargetTypes.NRF51)
        else:
            status = self._cload.reset_to_firmware(TargetTypes.STM32)

        if status:
            self.close()

        return status

    def close(self):
        if self._cload:
            self._cload.close()
            self._cload.link = None

    def _internal_flash(self, artifact: FlashArtifact, current_file_number=1, total_files=1, page_override=None):

        target_info = self._cload.targets[TargetTypes.from_string(artifact.target.target)]

        image = artifact.content
        t_data = target_info

        start_page = target_info.start_page
        if page_override is not None:
            start_page = page_override

        # If used from a UI we need some extra things for reporting progress
        factor = (100.0 * t_data.page_size) / len(image)
        progress = 0

        type_of_binary = 'Firmware'
        if artifact.target.type == 'bootloader+softdevice':
            type_of_binary = 'Bootloader+softdevice'

        if self.progress_cb:
            self.progress_cb(
                '{} ({}/{}) Starting...'.format(type_of_binary, current_file_number, total_files),
                int(progress))
        else:
            sys.stdout.write(
                'Flashing {} of {} to {} ({}): '.format(
                    current_file_number, total_files,
                    TargetTypes.to_string(t_data.id), artifact.target.type))
            sys.stdout.flush()

        if len(image) > ((t_data.flash_pages - start_page) *
                         t_data.page_size):
            if self.progress_cb:
                self.progress_cb('Error: Not enough space to flash the image file.', int(progress))
            else:
                print('Error: Not enough space to flash the image file.')
            raise Exception('Not enough space to flash the image file')

        if not self.progress_cb:
            logger.info(('%d bytes (%d pages) ' % (
                (len(image) - 1), int(len(image) / t_data.page_size) + 1)))
            sys.stdout.write(('%d bytes (%d pages) ' % (
                (len(image) - 1), int(len(image) / t_data.page_size) + 1)))
            sys.stdout.flush()

        # For each page
        ctr = 0  # Buffer counter
        for i in range(0, int((len(image) - 1) / t_data.page_size) + 1):
            if self.terminate_flashing_cb and self.terminate_flashing_cb():
                raise Exception('Flashing terminated')

            # Load the buffer
            if ((i + 1) * t_data.page_size) > len(image):
                self._cload.upload_buffer(
                    t_data.addr, ctr, 0, image[i * t_data.page_size:])
            else:
                self._cload.upload_buffer(
                    t_data.addr, ctr, 0,
                    image[i * t_data.page_size: (i + 1) * t_data.page_size])

            ctr += 1

            if self.progress_cb:
                progress += factor
                self.progress_cb('{} ({}/{}) Uploading buffer to {}...'.format(
                    type_of_binary,
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
                    self.progress_cb('{} ({}/{}) Writing buffer to {}...'.format(
                        type_of_binary,
                        current_file_number,
                        total_files,
                        TargetTypes.to_string(t_data.id)),

                        int(progress))
                else:
                    sys.stdout.write('%d' % ctr)
                    sys.stdout.flush()
                if not self._cload.write_flash(t_data.addr, 0,
                                               start_page + i - (ctr - 1),
                                               ctr):
                    if self.progress_cb:
                        self.progress_cb(
                            'Error during flash operation (code {})'.format(
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
                self.progress_cb('{} ({}/{}) Writing buffer to {}...'.format(
                    type_of_binary,
                    current_file_number,
                    total_files,
                    TargetTypes.to_string(t_data.id)),
                    int(progress))
            else:
                sys.stdout.write('%d' % ctr)
                sys.stdout.flush()
            if not self._cload.write_flash(
                    t_data.addr, 0,
                    (start_page + (int((len(image) - 1) / t_data.page_size)) -
                     (ctr - 1)), ctr):
                if self.progress_cb:
                    self.progress_cb(
                        'Error during flash operation (code {})'.format(
                            self._cload.error_code),
                        int(progress))
                else:
                    print('\nError during flash operation (code %d). Maybe'
                          ' wrong radio link?' % self._cload.error_code)
                raise Exception()

        sys.stdout.write('\n')
        sys.stdout.flush()

    def _get_platform_id(self):
        """Get platform identifier used in the zip manifest for curr copter"""
        identifier = 'cf1'
        if (BootVersion.is_cf2(self.protocol_version)):
            identifier = 'cf2'

        return identifier

    def console_callback(self, text: str):
        '''A callback to run when we get console text from Crazyflie'''
        # We do not add newlines to the text received, we get them from the
        # Crazyflie at appropriate places.
        print(text, end='')

    def _flash_deck_incrementally(self, artifacts: List[FlashArtifact], targets: List[Target], start_index: int,
                                  enable_console_log: Optional[bool] = False):
        flash_all_targets = len(targets) == 0
        if self.progress_cb:
            self.progress_cb('Identifying deck to be updated', 0)

        with SyncCrazyflie(self.clink, cf=Crazyflie()) as scf:
            if enable_console_log:
                scf.cf.console.receivedChar.add_callback(self.console_callback)

            deck_mems = scf.cf.mem.get_mems(MemoryElement.TYPE_DECK_MEMORY)
            deck_mems_count = len(deck_mems)
            if deck_mems_count == 0:
                return -1

            mgr = deck_memory.SyncDeckMemoryManager(deck_mems[0])
            try:
                decks = mgr.query_decks()
            except RuntimeError as e:
                if self.progress_cb:
                    message = f'Failed to read decks: {str(e)}'
                    self.progress_cb(message, 0)
                    logger.error(message)
                    time.sleep(2)
                    raise RuntimeError(message)

            # The decks dictionary uses the deck index as the key. Note that all indexes might not be present as some
            # decks do not support memory operations. decks.keys() might return the set {2, 4}.

            for deck_index in sorted(decks.keys()):
                deck = decks[deck_index]

                if self.terminate_flashing_cb and self.terminate_flashing_cb():
                    raise Exception('Flashing terminated')

                # Skip decks up to the start_index
                if deck_index < start_index:
                    continue

                # Check that we want to flash this deck
                deck_target = [t for t in targets if t == Target('deck', deck.name, 'fw', [], [])]
                if (not flash_all_targets) and len(deck_target) == 0:
                    print(f'Skipping {deck.name}, not in the target list')
                    continue

                # Check that we have an artifact for this deck
                deck_artifacts = [a for a in artifacts if a.target == Target('deck', deck.name, 'fw', [], [])]
                if len(deck_artifacts) == 0:
                    print(f'Skipping {deck.name}, no artifact for it in the .zip')
                    continue
                deck_artifact = deck_artifacts[0]

                if self.progress_cb:
                    self.progress_cb(f'Updating deck {deck.name}', 0)

                # Test and wait for the deck to be started
                timeout_time = time.time() + 5
                while not deck.is_started:
                    if time.time() > timeout_time:
                        raise RuntimeError(f'Deck {deck.name} did not start')
                    print('Deck not yet started ...')
                    time.sleep(0.5)
                    deck = mgr.query_decks()[deck_index]

                # Supports upgrades?
                if not deck.supports_fw_upgrade:
                    print(f'Deck {deck.name} does not support firmware update, skipping!')
                    continue

                # Reset to bootloader mode, if supported
                if deck.supports_reset_to_bootloader:
                    print(f'Deck {deck.name}, reset to bootloader')
                    deck.reset_to_bootloader()

                    time.sleep(0.1)
                    deck = mgr.query_decks()[deck_index]
                else:
                    # Is an upgrade required?
                    if not deck.is_fw_upgrade_required:
                        print(f'Deck {deck.name} firmware up to date, skipping')
                        continue

                # Wait for bootloader to be ready
                timeout_time = time.time() + 5
                while not deck.is_bootloader_active:
                    if time.time() > timeout_time:
                        raise RuntimeError(f'Deck {deck.name} did not enter bootloader mode')
                    print(f'Error: Deck {deck.name} bootloader not active yet...')
                    time.sleep(0.5)
                    deck = mgr.query_decks()[deck_index]

                progress_cb = self.progress_cb
                if not progress_cb:
                    def progress_cb(msg: str, percent: int):
                        frames = ['|', '/', '-', '\\']
                        frame = frames[int(percent) % 4]
                        print(f'{frame} {percent}% {msg}')

                # Flash the new firmware
                deck.set_fw_new_flash_size(len(deck_artifact.content))
                result = deck.write_sync(0, deck_artifact.content, progress_cb)
                if result:
                    if self.progress_cb:
                        self.progress_cb(f'Deck {deck.name} updated successful!', 100)
                else:
                    if self.progress_cb:
                        self.progress_cb(f'Failed to update deck {deck.name}', int(0))
                    raise RuntimeError(f'Failed to update deck {deck.name}')

                if enable_console_log:
                    # Wait a bit to let the console log print
                    time.sleep(6)

                # We flashed a deck, return for re-boot
                next_index = deck_index + 1
                return next_index

            # We have flashed the last deck
            return -1
