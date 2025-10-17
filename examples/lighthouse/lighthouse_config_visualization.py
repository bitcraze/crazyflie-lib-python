# -*- coding: utf-8 -*-
#
#     ||          ____  _ __
#  +------+      / __ )(_) /_______________ _____  ___
#  | 0xBC |     / __  / / __/ ___/ ___/ __ `/_  / / _ \
#  +------+    / /_/ / / /_/ /__/ /  / /_/ / / /_/  __/
#   ||  ||    /_____/_/\__/\___/_/   \__,_/ /___/\___/
#
#  Copyright (C) 2025 Bitcraze AB
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
Simple script for visualizing the Ligithouse positioning system's configuration
using matplotlib. Each base station is represented by a local coordinate frame, while
each one's coverage is represented by 2 circular sectors; a horizontal and a vertical one.
Notice that the base station coordinate frame is defined as:
    - X-axis pointing forward through the glass
    - Y-axis pointing right, when the base station is seen from the front.
    - Z-axis pointing up

To run the script, just change the path to your .yaml file.
"""
import matplotlib.pyplot as plt
import numpy as np
import yaml

config_file = 'lighthouse.yaml'  # Add the path to your .yaml file

Range = 5  # Range of each base station in meters
FoV_h = 150  # Horizontal Field of View in degrees
FoV_v = 110  # Vertical Field of View in degrees


def draw_coordinate_frame(ax, P, R, label='', length=0.5, is_bs=False):
    """Draw a coordinate frame at position t with orientation R."""
    x_axis = R @ np.array([length, 0, 0])
    y_axis = R @ np.array([0, length, 0])
    z_axis = R @ np.array([0, 0, length])

    ax.quiver(P[0], P[1], P[2], x_axis[0], x_axis[1], x_axis[2], color='r', linewidth=2)
    ax.quiver(P[0], P[1], P[2], y_axis[0], y_axis[1], y_axis[2], color='g', linewidth=2)
    ax.quiver(P[0], P[1], P[2], z_axis[0], z_axis[1], z_axis[2], color='b', linewidth=2)
    if is_bs:
        ax.scatter(P[0], P[1], P[2], s=50, color='black')
    ax.text(P[0], P[1], P[2], label, fontsize=10, color='black')


def draw_horizontal_sector(ax, P, R, radius=Range, angle_deg=FoV_h, color='r', alpha=0.3, n_points=50):
    """
    Draw a circular sector centered at the origin of the local coordinate frame,lying in
    the local XY-plane, so that its central axis is aligned with the positive X-axis.
    """
    # Angle range (centered on X-axis)
    half_angle = np.deg2rad(angle_deg / 2)
    thetas = np.linspace(-half_angle, half_angle, n_points)

    # Circle points in local XY-plane
    x_local = radius * np.cos(thetas)
    y_local = radius * np.sin(thetas)
    z_local = np.zeros_like(thetas)

    # Stack the coordinates into a 3xN matix
    pts_local = np.vstack([x_local, y_local, z_local])

    # Transfer the points to the global frame, creating a 3xN matrix
    pts_global = R @ pts_local + P.reshape(3, 1)

    # Close the sector by adding the center point at the start and end
    X = np.concatenate(([P[0]], pts_global[0, :], [P[0]]))
    Y = np.concatenate(([P[1]], pts_global[1, :], [P[1]]))
    Z = np.concatenate(([P[2]], pts_global[2, :], [P[2]]))

    # Plot filled sector
    ax.plot_trisurf(X, Y, Z, color=color, alpha=alpha, linewidth=0)


def draw_vertical_sector(ax, P, R, radius=Range, angle_deg=FoV_v, color='r', alpha=0.3, n_points=50):
    """
    Draw a circular sector centered at the origin of the local coordinate frame,lying in
    the local XZ-plane, so that its central axis is aligned with the positive X-axis.
    """
    # Angle range (centered on X-axis)
    half_angle = np.deg2rad(angle_deg / 2)
    thetas = np.linspace(-half_angle, half_angle, n_points)

    # Circle points in local XZ-plane
    x_local = radius * np.cos(thetas)
    y_local = np.zeros_like(thetas)
    z_local = radius * np.sin(thetas)

    # Stack the coordinates into a 3xN matix
    pts_local = np.vstack([x_local, y_local, z_local])

    # Transfer the points to the global frame, creating a 3xN matrix
    pts_global = R @ pts_local + P.reshape(3, 1)

    # Close the sector by adding the center point at the start and end
    X = np.concatenate(([P[0]], pts_global[0, :], [P[0]]))
    Y = np.concatenate(([P[1]], pts_global[1, :], [P[1]]))
    Z = np.concatenate(([P[2]], pts_global[2, :], [P[2]]))

    # Plot filled sector
    ax.plot_trisurf(X, Y, Z, color=color, alpha=alpha, linewidth=0)


if __name__ == '__main__':
    # Load the .yamnl file
    with open(config_file, 'r') as f:
        data = yaml.safe_load(f)
    geos = data['geos']

    fig = plt.figure()
    ax = fig.add_subplot(111, projection='3d')

    # Draw global frame
    draw_coordinate_frame(ax, np.zeros(3), np.eye(3), label='Global', length=1.0)

    # Draw local frames + sectors
    for key, geo in geos.items():
        origin = np.array(geo['origin'])
        rotation = np.array(geo['rotation'])
        draw_coordinate_frame(ax, origin, rotation, label=f'BS {key+1}', length=0.5, is_bs=True)

        # Local XY-plane sector
        draw_horizontal_sector(ax, origin, rotation, radius=Range, angle_deg=FoV_h, color='red', alpha=0.15)

        # Local YZ-plane sector
        draw_vertical_sector(ax, origin, rotation, radius=Range, angle_deg=FoV_v, color='red', alpha=0.15)

    ax.set_xlabel('X')
    ax.set_ylabel('Y')
    ax.set_zlabel('Z')
    ax.set_title('Lighthouse Visualization')

    # Set equal aspect ratio
    all_points = [np.array(geo['origin']) for geo in geos.values()]
    all_points.append(np.zeros(3))
    all_points = np.array(all_points)
    max_range = np.ptp(all_points, axis=0).max()
    mid = all_points.mean(axis=0)
    ax.set_xlim(mid[0] - max_range/2, mid[0] + max_range/2)
    ax.set_ylim(mid[1] - max_range/2, mid[1] + max_range/2)
    ax.set_zlim(mid[2] - max_range/2, mid[2] + max_range/2)

    plt.show()
