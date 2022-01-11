#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#     ||          ____  _ __
#  +------+      / __ )(_) /_______________ _____  ___
#  | 0xBC |     / __  / / __/ ___/ ___/ __ `/_  / / _ \
#  +------+    / /_/ / / /_/ /__/ /  / /_/ / / /_/  __/
#   ||  ||    /_____/_/\__/\___/_/   \__,_/ /___/\___/
#
#  Copyright (C) 2013 Bitcraze AB
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
Access the TOC cache for reading/writing. It supports both user
cache and dist cache.
"""
import json
import logging
import os
from glob import glob

from .log import LogTocElement  # noqa
from .param import ParamTocElement  # noqa

__author__ = 'Bitcraze AB'
__all__ = ['TocCache']

logger = logging.getLogger(__name__)


class TocCache():
    """
    Access to TOC cache. To turn of the cache functionality
    don't supply any directories.
    """

    def __init__(self, ro_cache=None, rw_cache=None):
        self._cache_files = []
        if (ro_cache):
            self._cache_files += glob(ro_cache + '/*.json')
        if (rw_cache):
            self._cache_files += glob(rw_cache + '/*.json')
            if not os.path.exists(rw_cache):
                os.makedirs(rw_cache)

        self._rw_cache = rw_cache

    def fetch(self, crc):
        """ Try to get a hit in the cache, return None otherwise """
        cache_data = None
        pattern = '%08X.json' % crc
        hit = None

        for name in self._cache_files:
            if (name.endswith(pattern)):
                hit = name

        if (hit):
            try:
                cache = open(hit)
                cache_data = json.load(cache,
                                       object_hook=self._decoder)
                cache.close()
            except Exception as exp:
                logger.warning('Error while parsing cache file [%s]:%s',
                               hit, str(exp))

        return cache_data

    def insert(self, crc, toc):
        """ Save a new cache to file """
        if self._rw_cache:
            try:
                filename = '%s/%08X.json' % (self._rw_cache, crc)
                cache = open(filename, 'w')
                cache.write(json.dumps(toc, indent=2,
                                       default=self._encoder))
                cache.close()
                logger.info('Saved cache to [%s]', filename)
                self._cache_files += [filename]
            except Exception as exp:
                logger.warning('Could not save cache to file [%s]: %s',
                               filename, str(exp))
        else:
            logger.warning('Could not save cache, no writable directory')

    def _encoder(self, obj):
        """ Encode a toc element leaf-node """
        encoded = {
            '__class__': obj.__class__.__name__,
            'ident': obj.ident,
            'group': obj.group,
            'name': obj.name,
            'ctype': obj.ctype,
            'pytype': obj.pytype,
            'access': obj.access,
        }

        if isinstance(obj, ParamTocElement):
            encoded['extended'] = obj.extended

        return encoded
        raise TypeError(repr(obj) + ' is not JSON serializable')

    def _decoder(self, obj):
        """ Decode a toc element leaf-node """
        if '__class__' in obj:
            elem = eval(obj['__class__'])()
            elem.ident = obj['ident']
            elem.group = str(obj['group'])
            elem.name = str(obj['name'])
            elem.ctype = str(obj['ctype'])
            elem.pytype = str(obj['pytype'])
            elem.access = obj['access']
            if isinstance(elem, ParamTocElement):
                elem.extended = obj['extended']
            return elem
        return obj
