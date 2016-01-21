#!/usr/bin/env python
# encoding=utf8 ---------------------------------------------------------------
# Project           : Parsing
# -----------------------------------------------------------------------------
# Author            : Sébastien Pierre
# License           : BSD License
# -----------------------------------------------------------------------------
# Creation date     : 18-Dec-2014
# Last modification : 21-Jan-2016
# -----------------------------------------------------------------------------

import sys, os, re, ctypes
from   os.path import dirname, join, abspath

try:
	import reporter as logging
except ImportError:
	import logging

# Loading the C library
VERSION            = "0.5.1"
LICENSE            = "http://ffctn.com/doc/licenses/bsd"
PACKAGE_PATH       = dirname(abspath(__file__))
LIB_PATHS          = [_ for _ in (os.path.join(_, "libparsing.so") for _ in (
	dirname(PACKAGE_PATH),
	dirname(dirname(PACKAGE_PATH))
)) if os.path.exists(_)]
assert LIB_PATHS, "libparsing: Cannot find libparsing.so"
LIBPARSING         = ctypes.cdll.LoadLibrary(LIB_PATHS[0])
assert LIBPARSING, "libparsing: Cannot load libparsing.so"

# Constants used in the source code
NOTHING                   = re
CARDINALITY_OPTIONAL      = '?'
CARDINALITY_ONE           = '1'
CARDINALITY_MANY_OPTIONAL = '*'
CARDINALITY_MANY          = '+'
TYPE_WORD                 = 'W'
TYPE_TOKEN                = 'T'
TYPE_GROUP                = 'G'
TYPE_RULE                 = 'R'
TYPE_CONDITION            = 'c'
TYPE_PROCEDURE            = 'p'
TYPE_REFERENCE            = '#'
STATUS_INIT               = '-'
STATUS_PROCESSING         = '~'
STATUS_MATCHED            = 'Y'
STATUS_FAILED             = 'X'
STATUS_INPUT_ENDED        = '.'
STATUS_ENDED              = 'E'
ID_BINDING                = -1
ID_UNBOUND                = -10
SELF                      = "self"

def wrap( value, type  ):
	"""Wraps the given cValue into the given Python type."""
	if issubclass(type, CObject):
		return type.Wrap(value)
	else:
		raise ValueError

def unwrap( value, self ):
	"""Unwraps the given Python object and returns its C value."""
	if isinstance(value, CObject):
		return value._cvalue
	elif isinstance(value, str):
		raise ValueError
	elif isinstance(value, unicode):
		raise ValueError
	elif isinstance(value, int):
		raise ValueError
	elif value is None:
		raise ValueError
	else:
		raise ValueError

class CObject(object):

	# CObjects can be pooled so that they can be easily recycled,
	# which is very usefultype for short-lived objects
	POOL_SIZE   = 0
	POOL        = None
	INITIALIZED = False
	METHODS     = {}

	@classmethod
	def Init( cls ):
		"""If the class is not already `INITIALIZED`, walks over the
		`METHODS` and invoke the `BindMethod` on each item. This will
		generate the wrapper methods for the C API."""
		if not cls.INITIALIZED:
			for k,v in cls.METHODS.items():
				ret =  v[-1]
				args = v[0:-1] if len(v) > 1 else []
				cls.BindMethod(k, args, ret )
			cls.INITIALIZED = True
		return cls

	@classmethod
	def BindMethod( cls, name, args, ret ):
		"""Creates a method wrapper and registers it in this class. This
		allows for the dynamic update of the API."""
		# If there is already a method with that name, we return it
		if hasattr(cls, name): return getattr(cls, name)
		# Otherwise we retrieve the symbol
		symbol = cls.__name__.rsplit(".",1)[-1] + "_" + name
		func   = LIBPARSING[symbol]
		if ret == SELF: ret = cls
		def method( self, *pargs ):
			# NOTE: Not sure why we're not using self here
			cargs = [unwrap(_) if _ != SELF else self._unwrap() for _ in pargs]
			res   = func(*cargs)
			if ret is SELF:
				self._wrap(res)
			else:
				return wrap(res, ret)
		# We register the method in the class
		setattr(cls, name, method)
		return method

	@classmethod
	def Wrap( cls, cValue ):
		""""Wraps the given C value in this C object."""
		if cls.POOL_SIZE and cls.POOL:
			# If there is a pool, we retrieve an object from it
			o = cls.POOL.pop()
			return o.wrap(cValue)
		else:
			# Otherwise we have to create a new one
			cls(cValue)

	def __init__( self, cValue=NOTHING ):
		# We lazily initialize the clases
		self.__class__.Init()
		self._cvalue = None
		if cValue is NOTHING:
			self.new(cValue)
		else:
			self._wrap(cValue)

	def _unwrap( self ):
		"""Returns the wrapped C value."""
		return self._cvalue

	def _wrap( self, cValue ):
		"""Wraps the given C value in this object. This requries that
		the C value is None."""
		# NOTE: In free, wrap might be called with a NULL pointer
		# Wraps the given C value
		assert self._cvalue is None
		self._cvalue = cValue
		return self

	def _reset( self ):
		if self._value: self.free()
		self._cvalue = None
		return self

	def __del__( self ):
		if self.POOL_SIZE:
			if self.__class__.POOL is None:
				self.__class__.POOL = []
			if len(self.__class__.POOL) < self.POOL_SIZE:
				self.__class__.POOL.append(self._reset())

class ParsingResult(CObject):
	pass

class Iterator(CObject):
	pass

class Grammar(CObject):

	METHODS = {
		"new"               : [SELF],
		"free"              : [SELF, None],
		"prepare"           : [SELF, None],
		"parseFromIterator" : (SELF, Iterator, ParsingResult),
		"parseFromPath"     : (SELF, str,      ParsingResult),
		"parseFromString"   : (SELF, str,      ParsingResult),
	}

# We initialize the main classes so that it doesn't have to be done later
# on.
[_.Init() for _ in (ParsingResult, Iterator, Grammar)]

# EOF - vim: ts=4 sw=4 noet