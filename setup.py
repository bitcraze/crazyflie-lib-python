#!/usr/bin/env python3
from setuptools import find_packages
from setuptools import setup

setup(
    name='cflib',
    version='0.1.13.1',
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
        'opencv-python-headless==4.5.1.48'
    ],

    # $ pip install -e .[dev]
    extras_require={
        'dev': [
            'pre-commit'
        ],
    },
)
