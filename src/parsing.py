#!/usr/bin/env python
# encoding=utf8 ---------------------------------------------------------------
# Project           : Parsing
# -----------------------------------------------------------------------------
# Author            : Sébastien Pierre
# License           : BSD License
# -----------------------------------------------------------------------------
# Creation date     : 2014-Dec-18
# Last modification : 2014-Dec-18
# -----------------------------------------------------------------------------

from ctypes import *

VERSION = "0.0.0"
LICENSE = "http://ffctn.com/doc/licenses/bsd"

_L      = CDLL("libparsing.so.0.1.2")

class Element(object):

	def __init__(self, *args):
		self._as_parameter = self.__class__.CREATE(*args)

class Word(Element):
	CREATE = lambda word: _L.Word_new(c_char_p(word))

class Token(Element):
	CREATE = lambda regexp: _L.Token_new(c_char_p(regexp))

class Grammar(Element):
	CREATE = lambda regexp: _L.Grammar_new()

# EOF - vim: ts=4 sw=4 noet
