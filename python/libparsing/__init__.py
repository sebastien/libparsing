#!/usr/bin/env python
# encoding=utf8 ---------------------------------------------------------------
# Project           : libparsing (Python bindings)
# -----------------------------------------------------------------------------
# Author            : FFunction
# License           : BSD License
# -----------------------------------------------------------------------------
# Creation date     : 2016-01-21
# Last modification : 2016-02-08
# -----------------------------------------------------------------------------

from __future__ import print_function

from   libparsing.api import *

try:
	import reporter as logging
except ImportError as e:
	import logging

VERSION = "0.7.3"
LICENSE = "http://ffctn.com/doc/licenses/bsd"
LIB     = Libparsing()

# TODO: Clear memory management/ownership/freeint
# TODO: Check weird stuff with Reference.element @property accessor
# TODO: Enable usage of C.CACHE, it seems that ctypes.addressof does not work
#       the way it is expected.

# NOTE: This ctypes implementation is noticeably longer than the corresponding
# CFII equivalent, while also being prone to random segfaults, which need
# to be investigated (memory management).

# particular, str have to be converted to bytes.

# SEE <http://stackoverflow.com/questions/23852311/different-behaviour-of-ctypes-c-char-p>

# EOF - vim: ts=4 sw=4 noet
