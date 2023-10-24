#!/usr/bin/env python3
from pathlib import Path

from setuptools import find_packages
from setuptools import setup
# read the contents of README.md file fo use in pypi description
directory = Path(__file__).parent
long_description = (directory / 'README.md').read_text()

setup(
    name='cflib',
    version='0.1.24',
    packages=find_packages(exclude=['examples', 'test']),

    description='Crazyflie python driver',
    url='https://github.com/bitcraze/crazyflie-lib-python',

    long_description=long_description,
    long_description_content_type='text/markdown',

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
        'libusb-package~=1.0',
        'scipy~=1.7',
        'numpy>=1.20,<1.25',
    ],

    # $ pip install -e .[dev]
    extras_require={
        'dev': [
            'pre-commit'
        ],
    },
)
