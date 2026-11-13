# -*- coding: utf-8 -*-
#
# ,---------,       ____  _ __
# |  ,-^-,  |      / __ )(_) /_______________ _____  ___
# | (  O  ) |     / __  / / __/ ___/ ___/ __ `/_  / / _ \
# | / ,--'  |    / /_/ / / /_/ /__/ /  / /_/ / / /_/  __/
#    +------`   /_____/_/\__/\___/_/   \__,_/ /___/\___/
#
# Copyright (C) 2026 Bitcraze AB
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
import unittest

from cflib.bootloader import _same_version


class BootloaderVersionCompareTest(unittest.TestCase):
    # Crazyflie reports 'major.minor.patch[+dev]', the release zip uses the tag name

    def test_release_matches_reported_version(self):
        self.assertTrue(_same_version('2024.10.0', '2024.10'))
        self.assertTrue(_same_version('2024.2.0', '2024.2'))

    def test_leading_zeros_are_ignored(self):
        self.assertTrue(_same_version('2026.4.0', '2026.04'))

    def test_different_versions_do_not_match(self):
        self.assertFalse(_same_version('2024.2.0', '2024.10'))
        self.assertFalse(_same_version('0.0.0', '2024.10'))

    def test_dev_build_does_not_match_release(self):
        self.assertFalse(_same_version('2024.10.0+dev', '2024.10'))
        self.assertFalse(_same_version('2024.1.0+dev', '2024.2'))

    def test_none_only_matches_none(self):
        self.assertTrue(_same_version(None, None))
        self.assertFalse(_same_version(None, '2024.10'))
        self.assertFalse(_same_version('2024.10.0', None))

    def test_unparsable_zip_version_does_not_match(self):
        # The zip's 'release' field is free text, a self-built zip could contain anything
        self.assertFalse(_same_version('2024.10.0', '2024.10-rc1'))
        self.assertFalse(_same_version('2024.10.0', 'garbage'))


if __name__ == '__main__':
    unittest.main()
