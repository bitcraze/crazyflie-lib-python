#!/usr/bin/env python3
import platform

from setuptools import find_packages
from setuptools import setup

extra_required = []
#
# For now we only require the CPP native radio link driver on x86_64
# since we only build and test on that platform. This will probably change.
# And probably faster if you request it.
#
if platform.machine() == 'x86_64':
    extra_required.extend(['cflinkcpp>=1.0a3'])

setup(
    name='cflib',
    version='0.1.15',
    packages=find_packages(exclude=['examples', 'tests']),

    description='Crazyflie python driver',
    url='https://github.com/bitcraze/crazyflie-lib-python',

    author='Bitcraze and contributors',
    author_email='contact@bitcraze.io',
    license='GPLv3',

    classifiers=[
        'Development Status :: 4 - Beta',
        'License :: OSI Approved :: GNU General Public License v3 (GPLv3)',
        'Topic :: System :: Hardware :: Hardware Drivers',
        'Programming Language :: Python :: 2',
        'Programming Language :: Python :: 3'
    ],

    keywords='driver crazyflie quadcopter',

    install_requires=[
        'pyusb>=1.0.0b2',
        'opencv-python-headless==4.5.1.48',
    ] + extra_required,

    # $ pip install -e .[dev]
    extras_require={
        'dev': [
            'pre-commit'
        ],
    },
)
