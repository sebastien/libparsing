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
	PACKAGE_PATH,
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

# This maintains a map between C type names and Python ctypes wrapper.
TYPES = {
	"void"            : None,
	"bool"            : ctypes.c_byte,
	"char"            : ctypes.c_char,
	"void*"           : ctypes.c_void_p,
	"char*"           : ctypes.c_char_p,
	"const char*"     : ctypes.c_char_p,
	"int"             : ctypes.c_int,
	"size_t"          : ctypes.c_uint,
	"Reference*"      : ctypes.c_void_p,
	"Element*"        : ctypes.c_void_p,
	"Element**"       : ctypes.POINTER(ctypes.c_void_p),
	"ParsingContext*" : ctypes.c_void_p,
}

# ------------------------------------------------------------------------------
#
# WRAPPING
#
# ------------------------------------------------------------------------------
#
# def wrap( value, type  ):
# 	"""Wraps the given cValue into the given Python type."""
# 	if issubclass(type, CObject):
# 		return type.Wrap(value)
# 	else:
# 		raise ValueError
#
# def unwrap( value, type=None ):
# 	"""Unwraps the given Python object and returns its C value."""
# 	return value
# 	# TODO: Ensure that the type matches
# 	if isinstance(value, CObject):
# 		return value._cvalue
# 	elif isinstance(value, str):
# 		return ctypes.c_char_p(value)
# 	elif isinstance(value, unicode):
# 		raise ValueError
# 	elif isinstance(value, int):
# 		return ctypes.c_int(value)
# 	elif isinstance(value, float):
# 		return ctypes.c_float(value)
# 	elif value is None:
# 		return None
# 	else:
# 		raise ValueError

def smartcast(value, type):
	"""Makes our best to convert the given value to the given type. If not
	successful, will return the value as it is."""
	print ("SMARTCAST", value, type)
	if isinstance(value, type):
		return value
	elif isinstance(value, TParsingElement):
		# Any ParsingElement subclass will be automatically cast to a
		# ParsingElement
		if ctypes.POINTER(value.__class__) == type:
			# We might not need to cast if the type is specific enough
			return ctypes.pointer(value)
		else:
			return ctypes.cast(ctypes.pointer(value), ctypes.POINTER(ParsingElement))
	else:
		print ("CASTING", value, "TO", type)
		return value

# TODO: This should probably inherit from structure directly
class CObject(ctypes.Structure):
	"""The CObject class wraps C values (pointers) in a Python object
	that defines methods mirroring (and wrapping) the corresponding
	C API. This is specifically designed for libparsing's C style."""

	# CObjects can be pooled so that they can be easily recycled,
	# which is very usefultype for short-lived objects
	C_NAME      = None
	METHODS     = {}
	PROPERTIES  = {}
	STRUCTURE   = None
	INITIALIZED = False

	@classmethod
	def FromCPointer( cls, pointer ):
		# FIXME: Maybe pointer.address?
		return cls.from_address(pointer)

	@classmethod
	def Init( cls ):
		"""If the class is not already `INITIALIZED`, walks over the
		`METHODS` and invoke the `BindMethod` on each item. This will
		generate the wrapper methods for the C API."""
		# NOTE: Testin cls.INITIALIZED does not work as it traverses the
		# type hierarchy.
		if "INITIALIZED" not in cls.__dict__:
			print ("INIT", cls)
			if not cls.C_NAME:
				cls.C_NAME = cls.__name__.rsplit(".",1)[-1]
			for k,v in cls.METHODS.items():
				ret =  v[-1]
				args = v[0:-1] if len(v) > 1 else []
				cls.BindMethod(k, args, ret )
			if cls.STRUCTURE:
				fields = cls.ParseStructure(cls.STRUCTURE)
				assert not hasattr(cls, "_fields_")
				try:
					cls._fields_ = fields
				except AttributeError as e:
					print ("FUXK", e)
			cls.INITIALIZED = True
		return cls

	@classmethod
	def BindMethod( cls, name, args, ret ):
		"""Creates a method wrapper and registers it in this class. This
		allows for the dynamic update of the API."""
		# If there is already a method with that name, we return it
		if hasattr(cls, name): return getattr(cls, name)
		# Otherwise we retrieve the symbol
		symbol = cls.C_NAME+ "_" + name
		func   = LIBPARSING[symbol]
		if ret == SELF: ret = cls
		# We ensure that the ctypes call has proper typing
		ctargs = []
		for a in args:
			cta = None
			if a == SELF:
				cta = ctypes.POINTER(cls)
			elif issubclass(a, CObject):
				cta = ctypes.POINTER(a)
			elif a == str:
				cta = ctypes.c_char_p
			elif a == float:
				cta = ctypes.c_float
			elif a == int:
				cta = ctypes.c_int
			elif a == chr:
				cta = ctypes.c_char
			else:
				raise ValueError("Cannot get ctypes equivalent for {0}".format(a))
		func.argtypes= ctargs
		# The method function will automatically wrap the call, including
		# its arguments and return value based on `args` and ` ret`.
		if args and args[0] == SELF:
			is_method = True
			delta     = 1
		else:
			is_method = False
			delta     = 0
		# http://python.net/crew/theller/ctypes/tutorial.html#calling-functions
		# TODO: Add restype for method
		def method( self, *pargs ):
			# If SELF is the first argument, the we have a method, and we will
			# automatically insert the SELF value.
			assert len(pargs) == (len(args) - delta), "{0}: {1} arguments required, {2} given: {3}".format(symbol, len(args) - delta, len(pargs), pargs)
			#cargs = [unwrap(_, args[i + delta]) if _ != SELF else self._ounwrap() for i,_ in enumerate(pargs)]
			cargs = pargs
			print ("Invoking", symbol, "with", cargs, "from", pargs)
			# NOTE: using `byref` is faster than using `pointer`. Ctypes is
			# supposed to do this conversion automatically, though.
			# SEE: http://devdocs.io/python/library/ctypes#1.9
			res   = func(ctypes.pointer(self), *cargs) if is_method else func(*cargs)
			print ("-->", res)
			if ret is SELF:
				return self
			else:
				# TODO: Maybe we should cToPython this value
				return ret
		# We register the method in the class
		setattr(cls, name, method)
		return method

	@classmethod
	def ParseStructure( cls, text ):
		res = []
		for line in text.split("\n"):
			line = line.split(";",1)[0]
			line = [_.strip() for _ in line.split()]
			line = [_ for _ in line if _ and _ != "struct"]
			if not line: continue
			name = line[-1]
			type = " ".join(line[0:-1])
			if "->" in type:
				# We handle function pointers
				type = type.split("->")
				type = ctypes.CFUNCTYPE(*[TYPES[_] for _ in type if _ != "void"])
			else:
				# Otherwise it's just a regular type
				type = TYPES[type]
			res.append((name, type))
			cls.PROPERTIES[name] = type
		return res

	def __init__( self, *args ):
		# We lazily initialize the clases
		ctypes.Structure.__init__(self)
		self.__class__.Init()
		print "INVOKING CONSTRUCTOR", self
		if hasattr(self, "new"):
			self.new(*args)

	def XXX__del__( self ):
		if hasattr(self, "free"):
			self.free()

	def XXX__getattribute__(self, name):
		print ("XXX NAME", self, name)
		if name in self.PROPERTIES:
			type = self.PROPERTIES[name]
			value = Structure.__getattr__(self, name)
			if isinstance(type.CObject):
				print "COBECT", value
				return value.address
			else:
				return value
		else:
			return Structure.__getattr__(self, name)


class Match(CObject):
	"""Matches cannot be created directly through the API, but are
	retrieved as part of `ParsingResult`."""

	POOL_SIZE = 100
	STRUCTURE = """
	char            status;     // The status of the match (see STATUS_XXX)
	size_t          offset;     // The offset of `iterated_t` matched
	size_t          length;     // The number of `iterated_t` matched
	Element*        element;
	ParsingContext* context;
	void*           data;      // The matched data (usually a subset of the input stream)
	struct Match*   next;      // A pointer to the next  match (see `References`)
	struct Match*   child;
	"""

	def walk( self, callback ):
		pass

# -----------------------------------------------------------------------------
#
# PARSING ELEMENT
#
# -----------------------------------------------------------------------------

class ParsingElement(CObject):

	STRUCTURE = """
		char           type;
		int            id;
		const char*    name;       // The parsing element's name, for debugging
		void*          config;     // The configuration of the parsing element
		struct Reference*     children;   // The parsing element's children, if any
		ParsingElement*->ParsingContext*->Match* recognize;
		ParsingElement*->ParsingContext*->Match*->Match* process;
		Match*->void freeMatch;
	"""

class CompositeParsingElement(ParsingElement):

	def add( self, *children ):
		for c in children:
			assert isinstance(c, ParsingElement) # or isinstance(c, Reference)
			#LIBPARSING.ParsingElement_add(self._cvalue, c)
		return self

	def append( self, *children ):
		return self.add(*children)

	def set( self, *children ):
		return self.add(*children)

	#def disableMemoize( self ):
	#	return self

	#def disableFailMemoize( self ):
	#	return self

class PythonParsingElement:
	pass

class Word(CObject, PythonParsingElement):

	STRUCTURE = ParsingElement.STRUCTURE
	METHODS   = dict(
		new = [str, SELF]
	)

class ParsingContext(CObject):
	pass

class ParsingResult(CObject):
	pass

class Iterator(CObject):
	pass

class Grammar(CObject):

	STRUCTURE = """
	ParsingElement*  axiom;       // The axiom
	ParsingElement*  skip;        // The skipped element
	int              axiomCount;  // The count of parsing elemetns in axiom
	int              skipCount;   // The count of parsing elements in skip
	Element**        elements;    // The set of all elements in the grammar
	bool             isVerbose;
	"""

	METHODS = {
		"new"               : [SELF],
		"free"              : [SELF, None],
		"prepare"           : [SELF, None],
		"parseFromIterator" : (SELF, Iterator, ParsingResult),
		"parseFromPath"     : (SELF, str,      ParsingResult),
		"parseFromString"   : (SELF, str,      ParsingResult),
	}

	def __setattr__( self, name, value ):
		field_type = self.PROPERTIES.get(name)
		if field_type:
			return CObject.__setattr__(self, name, smartcast(value, field_type))
		else:
			return CObject.__setattr__(self, name, value)

# We initialize the main classes so that it doesn't have to be done later
# on.
for _ in (Match, ParsingContext, ParsingElement, Word, Iterator, Grammar):
	c_name = _.C_NAME or _.__name__.rsplit(".",1)[-1]
	TYPES[c_name + "*"] = ctypes.POINTER(_)
	_.Init()

# EOF - vim: ts=4 sw=4 noet
