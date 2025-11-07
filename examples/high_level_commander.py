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

import argparse
import time

from cflib._rust import Crazyflie


def main() -> None:
    # parser = argparse.ArgumentParser(description="TODO
    # parser.add_argument(
    #     "uri",
    #     nargs="?",
    #     default="radio://0/80/2M/E7E7E7E7E7",
    #     help="Crazyflie URI (default: radio://0/80/2M/E7E7E7E7E7)",
    # )
    # args: argparse.Namespace = parser.parse_args()
    uri = "radio://0/80/2M/E7E7E7E7E7"

    print(f"Connecting to {uri}...")
    cf = Crazyflie.connect_from_uri(uri)
    print("Connected!")

    high_level_commander = cf.high_level_commander()
    high_level_commander.take_off(0.2, 0, 2, 0)


if __name__ == "__main__":
    main()
